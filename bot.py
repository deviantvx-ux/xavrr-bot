"""XAVRR GAMING: Telegram bot + Flask API + SQLite (single process).
Env vars:
BOT_TOKEN     token from BotFather (required)
WEBAPP_URL    public HTTPS url of this server (Mini App url)
DEMO_MODE     1 (default) = test credits, no real payments/withdrawals; 0 = real Stars
ADMIN_IDS     comma separated Telegram ids with access to the admin tab
GIFT_IDS      JSON {"heart":"<gift_id>", ...}, ids from Bot API getAvailableGifts
DB_PATH       sqlite file (default xavrr.db)
PORT          default 8080
DEV_AUTH      1 = allow ?dev=<id> without Telegram (LOCAL TESTING ONLY)
"""
import os, json, time, hmac, hashlib, secrets, sqlite3, threading, uuid, logging
from contextlib import contextmanager
from functools import wraps
from urllib.parse import parse_qsl
import requests
from flask import Flask, request, jsonify, send_from_directory, g
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("xavrr")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
DEMO = os.environ.get("DEMO_MODE", "1") == "1"
DEV_AUTH = os.environ.get("DEV_AUTH", "0") == "1"
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}
GIFT_IDS = json.loads(os.environ.get("GIFT_IDS", "{}"))
DB_PATH = os.environ.get("DB_PATH", "xavrr.db")
PORT = int(os.environ.get("PORT", "8080"))
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
HERE = os.path.dirname(os.path.abspath(file))
START_CREDITS = 1000 if DEMO else 0
SELL_RATE = 0.9          # sell-back share of item value
UPGRADE_EDGE = 0.95      # upgrade chance multiplier (house edge 5%)
key: (name, emoji, value in credits). 1 Telegram Star = 1 credit.
ITEMS = {
"heart": ("Heart", "💝", 50), "bear": ("Teddy Bear", "🧸", 50),
"rose": ("Rose", "🌹", 100), "cake": ("Cake", "🎂", 100),
"rocket": ("Rocket", "🚀", 100), "trophy": ("Trophy", "🏆", 100),
"diamond": ("Diamond", "💎", 250), "crown": ("Crown", "👑", 500),
"ring": ("Ring", "💍", 1000), "star": ("Golden Star", "⭐", 2000),
}
drops: item -> integer weight (sum 100). Expected value must stay below price.
CASES = {
"starter": {"name": "Starter", "price": 75,
"drops": {"heart": 45, "bear": 35, "rose": 13, "rocket": 5, "diamond": 2}},
"gold": {"name": "Gold", "price": 200,
"drops": {"rose": 40, "cake": 25, "trophy": 15, "diamond": 12, "crown": 6, "ring": 2}},
"royal": {"name": "Royal", "price": 600,
"drops": {"diamond": 55, "crown": 30, "ring": 12, "star": 3}},
}
for _id, _c in CASES.items():
_ev = sum(ITEMS[k][2] * w for k, w in _c["drops"].items()) / sum(_c["drops"].values())
if _ev >= _c["price"]:
log.warning("case %s has EV %.1f >= price %s", _id, _ev, _c["price"])
rng = secrets.SystemRandom()
app = Flask(name)
class ApiError(Exception):
def init(self, msg, code=400):
super().init(msg)
self.msg, self.code = msg, code
@app.errorhandler(ApiError)
def _api_err(e):
return jsonify({"error": e.msg}), e.code
@app.errorhandler(Exception)
def _any_err(e):
log.exception("unhandled")
return jsonify({"error": "Помилка сервера"}), 500
---------------------------------------------------------------- database
def connect():
c = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
c.row_factory = sqlite3.Row
c.execute("PRAGMA journal_mode=WAL")
return c
def db():
if "db" not in g:
g.db = connect()
return g.db
@app.teardown_appcontext
def close():
c = g.pop("db", None)
if c:
c.close()
@contextmanager
def txn(con):
con.execute("BEGIN IMMEDIATE")
try:
yield
con.execute("COMMIT")
except BaseException:
con.execute("ROLLBACK")
raise
def init_db():
con = connect()
con.executescript("""
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, username TEXT,
balance INTEGER NOT NULL DEFAULT 0 CHECK(balance>=0), created INTEGER);
CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
item_key TEXT NOT NULL, value INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'owned', created INTEGER);
CREATE TABLE IF NOT EXISTS tx(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
kind TEXT NOT NULL, amount INTEGER NOT NULL, meta TEXT, created INTEGER);
CREATE TABLE IF NOT EXISTS payments(charge_id TEXT PRIMARY KEY, user_id INTEGER, amount INTEGER, created INTEGER);
CREATE TABLE IF NOT EXISTS requests(user_id INTEGER, req_id TEXT, result TEXT, created INTEGER,
PRIMARY KEY(user_id, req_id));
CREATE INDEX IF NOT EXISTS inv_user ON inventory(user_id, status);
CREATE INDEX IF NOT EXISTS tx_user ON tx(user_id, id);
""")
con.close()
def log_tx(con, uid, kind, amount, meta=""):
con.execute("INSERT INTO tx(user_id,kind,amount,meta,created) VALUES(?,?,?,?,?)",
(uid, kind, amount, str(meta), now()))
def credit(con, uid, amount, kind, meta=""):
con.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, uid))
log_tx(con, uid, kind, amount, meta)
def spend(con, uid, amount, kind, meta=""):
cur = con.execute("UPDATE users SET balance=balance-? WHERE id=? AND balance>=?", (amount, uid, amount))
if cur.rowcount != 1:
raise ApiError("Недостатньо балансу", 402)
log_tx(con, uid, kind, -amount, meta)
def balance(con, uid):
return con.execute("SELECT balance FROM users WHERE id=?", (uid,)).fetchone()[0]
def ensure_user(con, u):
"""Call inside a transaction."""
name = (u.get("first_name", "") + " " + u.get("last_name", "")).strip() or "Player"
exists = con.execute("SELECT 1 FROM users WHERE id=?", (u["id"],)).fetchone()
if exists:
con.execute("UPDATE users SET name=?, username=? WHERE id=?", (name, u.get("username"), u["id"]))
else:
con.execute("INSERT INTO users(id,name,username,balance,created) VALUES(?,?,?,?,?)",
(u["id"], name, u.get("username"), START_CREDITS, now()))
if START_CREDITS:
log_tx(con, u["id"], "start_bonus", START_CREDITS, "demo")
def to_int(v, name="value"):
try:
return int(v)
except (TypeError, ValueError):
raise ApiError(f"Некоректне поле {name}")
def item_json(iid, key, value=None):
n, e, v = ITEMS[key]
return {"id": iid, "key": key, "name": n, "emoji": e, "value": value if value is not None else v}
-------------------------------------------------------------------- auth
def verify_init_data(init):
data = dict(parse_qsl(init, keep_blank_values=True))
h = data.pop("hash", None)
if not h or "user" not in data:
return None
check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
calc = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
if not hmac.compare_digest(calc, h):
return None
if now() - to_int(data.get("auth_date", 0)) > 86400:
return None
return json.loads(data["user"])
def auth(fn):
@wraps(fn)
def w(*a, **kw):
user = None
if DEV_AUTH and request.headers.get("X-Dev-User"):
user = {"id": to_int(request.headers["X-Dev-User"]), "first_name": "Dev"}
else:
user = verify_init_data(request.headers.get("X-Init-Data", ""))
if not user:
raise ApiError("Не вдалося перевірити Telegram-сесію. Відкрий застосунок із бота.", 401)
con = db()
with txn(con):
ensure_user(con, user)
g.uid = user["id"]
return fn(*a, **kw)
return w
def run_once(fn):
"""Idempotency: the same req_id returns the stored result instead of running twice."""
req_id = str((request.get_json(silent=True) or {}).get("req_id", ""))
if not req_id or len(req_id) > 64:
raise ApiError("req_id обов’язковий")
con, uid = db(), g.uid
with txn(con):
row = con.execute("SELECT result FROM requests WHERE user_id=? AND req_id=?", (uid, req_id)).fetchone()
if row:
return json.loads(row[0])
res = fn(con)
con.execute("INSERT INTO requests VALUES(?,?,?,?)", (uid, req_id, json.dumps(res), now()))
return res
def pick(drops):
r = rng.randrange(sum(drops.values()))
for k, w in drops.items():
if r < w:
return k
r -= w
def upgrade_chance(src, target):
return round(min(80.0, max(1.0, src / target * 100 * UPGRADE_EDGE)), 2)
--------------------------------------------------------------------- API
@app.get("/")
def index():
return send_from_directory(os.path.join(HERE, "webapp"), "index.html")
@app.get("/api/me")
@auth
def me():
con, uid = db(), g.uid
u = con.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
inv = [item_json(r["id"], r["item_key"], r["value"]) for r in con.execute(
"SELECT id,item_key,value FROM inventory WHERE user_id=? AND status='owned' ORDER BY id DESC", (uid,))]
cases = []
for cid, c in CASES.items():
tot = sum(c["drops"].values())
cases.append({"id": cid, "name": c["name"], "price": c["price"],
"drops": [{"key": k, "chance": round(w * 100 / tot, 2)} for k, w in c["drops"].items()]})
return jsonify({
"user": {"id": uid, "name": u["name"], "username": u["username"]},
"balance": u["balance"], "demo": DEMO, "admin": uid in ADMIN_IDS,
"inventory": inv, "cases": cases, "edge": UPGRADE_EDGE, "sell_rate": SELL_RATE,
"items": {k: {"name": v[0], "emoji": v[1], "value": v[2]} for k, v in ITEMS.items()},
})
@app.post("/api/open")
@auth
def open_case():
cid = (request.get_json(silent=True) or {}).get("case")
case = CASES.get(cid)
if not case:
raise ApiError("Кейс не знайдено", 404)
uid = g.uid
def go(con):
    spend(con, uid, case["price"], "case_open", cid)
    key = pick(case["drops"])
    cur = con.execute("INSERT INTO inventory(user_id,item_key,value,status,created) VALUES(?,?,?,'owned',?)",
                      (uid, key, ITEMS[key][2], now()))
    return {"item": item_json(cur.lastrowid, key), "balance": balance(con, uid)}
return jsonify(run_once(go))
@app.post("/api/upgrade")
@auth
def upgrade():
b = request.get_json(silent=True) or {}
tkey, mode, uid = b.get("target"), b.get("mode"), g.uid
if tkey not in ITEMS:
raise ApiError("Невідома ціль", 404)
tv = ITEMS[tkey][2]
def go(con):
    if mode == "gift":
        iid = to_int(b.get("item_id"), "item_id")
        row = con.execute("SELECT value FROM inventory WHERE id=? AND user_id=? AND status='owned'",
                          (iid, uid)).fetchone()
        if not row:
            raise ApiError("Подарунок не знайдено", 404)
        src = row["value"]
        if src >= tv:
            raise ApiError("Ціль має бути дорожчою за подарунок")
        if con.execute("UPDATE inventory SET status='burned' WHERE id=? AND status='owned'", (iid,)).rowcount != 1:
            raise ApiError("Подарунок недоступний")
    elif mode == "balance":
        src = to_int(b.get("stake"), "stake")
        if src < 10 or src >= tv:
            raise ApiError("Некоректна ставка")
        spend(con, uid, src, "upgrade_stake", tkey)
    else:
        raise ApiError("Невідомий режим")
    chance = upgrade_chance(src, tv)
    win = rng.random() * 100 < chance
    out = None
    if win:
        cur = con.execute("INSERT INTO inventory(user_id,item_key,value,status,created) VALUES(?,?,?,'owned',?)",
                          (uid, tkey, tv, now()))
        out = item_json(cur.lastrowid, tkey)
    log_tx(con, uid, "upgrade_win" if win else "upgrade_lose", 0, f"{mode}:{src}->{tkey}@{chance}")
    return {"win": win, "chance": chance, "item": out, "balance": balance(con, uid)}
return jsonify(run_once(go))
@app.post("/api/sell")
@auth
def sell():
iid, uid = to_int((request.get_json(silent=True) or {}).get("item_id"), "item_id"), g.uid
con = db()
with txn(con):
row = con.execute("SELECT value FROM inventory WHERE id=? AND user_id=? AND status='owned'",
(iid, uid)).fetchone()
if not row:
raise ApiError("Подарунок не знайдено", 404)
con.execute("UPDATE inventory SET status='sold' WHERE id=?", (iid,))
amount = int(row["value"] * SELL_RATE)
credit(con, uid, amount, "sell", iid)
return jsonify({"amount": amount, "balance": balance(con, uid)})
@app.post("/api/withdraw")
@auth
def withdraw():
iid, uid = to_int((request.get_json(silent=True) or {}).get("item_id"), "item_id"), g.uid
if DEMO:
raise ApiError("У демо-режимі виведення вимкнене", 403)
con = db()
with txn(con):
row = con.execute("SELECT item_key FROM inventory WHERE id=? AND user_id=? AND status='owned'",
(iid, uid)).fetchone()
if not row:
raise ApiError("Подарунок не знайдено", 404)
gift_id = GIFT_IDS.get(row["item_key"])
if not gift_id:
raise ApiError("Для цього подарунка не налаштовано gift_id", 501)
con.execute("UPDATE inventory SET status='withdrawing' WHERE id=?", (iid,))
ok = False
try:
r = tg("sendGift", user_id=uid, gift_id=gift_id)
ok = bool(r.get("ok"))
if not ok:
log.error("sendGift failed: %s", r)
except Exception:
log.exception("sendGift error")
with txn(con):
con.execute("UPDATE inventory SET status=? WHERE id=?", ("withdrawn" if ok else "owned", iid))
log_tx(con, uid, "withdraw" if ok else "withdraw_failed", 0, iid)
if not ok:
raise ApiError("Не вдалося надіслати подарунок. Спробуй пізніше.", 502)
return jsonify({"ok": True})
@app.post("/api/deposit/stars")
@auth
def deposit_stars():
if DEMO:
raise ApiError("У демо-режимі реальні платежі вимкнені", 403)
amount = to_int((request.get_json(silent=True) or {}).get("amount"), "amount")
if not 50 <= amount <= 10000:
raise ApiError("Сума від 50 до 10000")
r = tg("createInvoiceLink", title="XAVRR: поповнення", description=f"{amount} кредитів",
payload=f"dep:{g.uid}:{uuid.uuid4().hex}", currency="XTR",
prices=[{"label": "Кредити", "amount": amount}])
if not r.get("ok"):
log.error("invoice failed: %s", r)
raise ApiError("Не вдалося створити рахунок", 502)
return jsonify({"link": r["result"]})
@app.post("/api/deposit/demo")
@auth
def deposit_demo():
if not DEMO:
raise ApiError("Доступно лише в демо-режимі", 403)
con, uid = db(), g.uid
with txn(con):
last = con.execute("SELECT created FROM tx WHERE user_id=? AND kind='demo_topup' ORDER BY id DESC LIMIT 1",
(uid,)).fetchone()
if last and now() - last[0] < 30:
raise ApiError("Зачекай 30 секунд")
credit(con, uid, 500, "demo_topup", "test")
return jsonify({"balance": balance(con, uid)})
@app.get("/api/history")
@auth
def history():
rows = db().execute("SELECT kind,amount,meta,created FROM tx WHERE user_id=? ORDER BY id DESC LIMIT 50", (g.uid,))
return jsonify([dict(r) for r in rows])
def admin_only(fn):
@wraps(fn)
def w(*a, **kw):
if g.uid not in ADMIN_IDS:
raise ApiError("Немає доступу", 403)
return fn(*a, **kw)
return w
@app.get("/api/admin/stats")
@auth
@admin_only
def admin_stats():
q = lambda s: db().execute(s).fetchone()[0] or 0
return jsonify({
"users": q("SELECT COUNT() FROM users"),
"balances": q("SELECT SUM(balance) FROM users"),
"opens": q("SELECT COUNT() FROM tx WHERE kind='case_open'"),
"spent_on_cases": -q("SELECT SUM(amount) FROM tx WHERE kind='case_open'"),
"stars_received": q("SELECT SUM(amount) FROM payments"),
"withdrawn": q("SELECT COUNT() FROM inventory WHERE status='withdrawn'"),
"stuck_withdrawals": q("SELECT COUNT() FROM inventory WHERE status='withdrawing'"),
})
@app.post("/api/admin/grant")
@auth
@admin_only
def admin_grant():
b = request.get_json(silent=True) or {}
target, amount = to_int(b.get("user_id"), "user_id"), to_int(b.get("amount"), "amount")
con = db()
with txn(con):
if not con.execute("SELECT 1 FROM users WHERE id=?", (target,)).fetchone():
raise ApiError("Користувача не знайдено", 404)
if amount < 0:
spend(con, target, -amount, "admin_adjust", g.uid)
else:
credit(con, target, amount, "admin_grant", g.uid)
return jsonify({"balance": balance(con, target)})
------------------------------------------------------------ Telegram bot
def handle_update(up):
if "pre_checkout_query" in up:
q = up["pre_checkout_query"]
ok = q.get("currency") == "XTR" and str(q.get("invoice_payload", "")).startswith("dep:")
tg("answerPreCheckoutQuery", pre_checkout_query_id=q["id"], ok=ok,
error_message=None if ok else "Некоректний платіж")
return
msg = up.get("message")
if not msg:
return
sp = msg.get("successful_payment")
if sp:
uid = msg["from"]["id"]
parts = sp.get("invoice_payload", "").split(":")
if len(parts) != 3 or parts[0] != "dep" or parts[1] != str(uid) or sp.get("currency") != "XTR":
log.error("bad payment payload: %s", sp)
return
con = connect()
try:
with txn(con):
ensure_user(con, msg["from"])
try:
con.execute("INSERT INTO payments VALUES(?,?,?,?)",
(sp["telegram_payment_charge_id"], uid, sp["total_amount"], now()))
except sqlite3.IntegrityError:
return  # already credited
credit(con, uid, sp["total_amount"], "deposit_stars", sp["telegram_payment_charge_id"])
finally:
con.close()
tg("sendMessage", chat_id=uid, text=f"Баланс поповнено на {sp['total_amount']} кр.")
return
if (msg.get("text") or "").startswith("/start") and WEBAPP_URL:
tg("sendMessage", chat_id=msg["chat"]["id"], text="Ласкаво просимо до XAVRR GAMING.",
reply_markup={"inline_keyboard": [[{"text": "Відкрити XAVRR", "web_app": {"url": WEBAPP_URL}}]]})
def poll():
tg("deleteWebhook")
offset = 0
while True:
try:
r = tg("getUpdates", offset=offset, timeout=30, allowed_updates=["message", "pre_checkout_query"])
for up in r.get("result", []):
offset = up["update_id"] + 1
try:
handle_update(up)
except Exception:
log.exception("update failed")
except Exception:
log.exception("poll error")
time.sleep(3)
if name == "main":
if not BOT_TOKEN:
raise SystemExit("Set BOT_TOKEN env var")
init_db()
log.info("Mode: %s", "DEMO (test credits)" if DEMO else "REAL")
threading.Thread(target=poll, daemon=True).start()
app.run(host="0.0.0.0", port=PORT, threaded=True)
