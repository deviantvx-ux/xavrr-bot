import asyncio
import json
import logging
import os
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ReplyKeyboardMarkup,
    WebAppInfo,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBAPP_URL = os.getenv(
    "WEBAPP_URL", "https://xavrr-bot.onrender.com/webapp/index.html"
).strip()
ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
DB_PATH = os.getenv("DB_PATH", "xavrr_gift.db").strip()
PORT = int(os.getenv("PORT", "10000").strip())

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN missing")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("xavrr_gift_bot")

TEXTS: Dict[str, Dict[str, str]] = {
    "uk": {
        "open_app": "💎 Відкрити XAVRR GIFT",
        "cases": "🎁 Кейси",
        "inv": "📦 Інвентар",
        "topup": "⭐ Баланс / Поповнити",
        "lang_btn": "🌐 Мова / Language",
        "start": (
            "💎 <b>XAVRR GIFT</b>\n"
            "Профіль: <b>{name}</b> (<code>{uid}</code>)\n"
            "Баланс: <b>{stars} ⭐</b>\n"
            "Промокод: <code>XAVRR</code> (+500 ⭐)\n"
            "Реферал: <code>{ref}</code>"
        ),
        "choose_lang": "🌐 Оберіть мову / Choose language / Выберите язык:",
        "lang_set": "✅ Мову змінено на <b>Українська</b>.",
        "cases_hdr": "🎁 Оберіть кейс з NFT-подарунками або відкрийте Mini App:",
        "empty_inv": "📦 Інвентар порожній. Відкрийте кейс!",
        "bal_msg": "⭐ Ваш баланс: <b>{stars} ⭐</b>",
        "no_stars": "Недостатньо зірок! Потрібно {price} ⭐",
        "sold": "✅ Продано за <b>+{earned} ⭐</b> | Баланс: <b>{bal} ⭐</b>",
        "wd_ok": "📤 Заявка <b>#{wid}</b> на <b>{item}</b> ({nick}) створена.",
        "promo_used": "⚠️ Промокод уже використано.",
        "promo_ok": "🎉 Промокод активовано: <b>+{bonus} ⭐</b> | Баланс: <b>{bal} ⭐</b>",
    },
    "en": {
        "open_app": "💎 Open XAVRR GIFT",
        "cases": "🎁 Cases",
        "inv": "📦 Inventory",
        "topup": "⭐ Balance / Top up",
        "lang_btn": "🌐 Language",
        "start": (
            "💎 <b>XAVRR GIFT</b>\n"
            "Profile: <b>{name}</b> (<code>{uid}</code>)\n"
            "Balance: <b>{stars} ⭐</b>\n"
            "Promo: <code>XAVRR</code> (+500 ⭐)\n"
            "Referral: <code>{ref}</code>"
        ),
        "choose_lang": "🌐 Choose language / Оберіть мову / Выберите язык:",
        "lang_set": "✅ Language switched to <b>English</b>.",
        "cases_hdr": "🎁 Choose a Telegram NFT case or open Mini App:",
        "empty_inv": "📦 Inventory is empty. Open a case!",
        "bal_msg": "⭐ Your balance: <b>{stars} ⭐</b>",
        "no_stars": "Not enough stars! Need {price} ⭐",
        "sold": "✅ Sold for <b>+{earned} ⭐</b> | Balance: <b>{bal} ⭐</b>",
        "wd_ok": "📤 Request <b>#{wid}</b> for <b>{item}</b> ({nick}) created.",
        "promo_used": "⚠️ Promo code already used.",
        "promo_ok": "🎉 Promo activated: <b>+{bonus} ⭐</b> | Balance: <b>{bal} ⭐</b>",
    },
    "ru": {
        "open_app": "💎 Открыть XAVRR GIFT",
        "cases": "🎁 Кейсы",
        "inv": "📦 Инвентарь",
        "topup": "⭐ Баланс / Пополнить",
        "lang_btn": "🌐 Язык",
        "start": (
            "💎 <b>XAVRR GIFT</b>\n"
            "Профиль: <b>{name}</b> (<code>{uid}</code>)\n"
            "Баланс: <b>{stars} ⭐</b>\n"
            "Промокод: <code>XAVRR</code> (+500 ⭐)\n"
            "Реферал: <code>{ref}</code>"
        ),
        "choose_lang": "🌐 Выберите язык / Choose language / Оберіть мову:",
        "lang_set": "✅ Язык изменён на <b>Русский</b>.",
        "cases_hdr": "🎁 Выберите кейс с NFT-подарками или откройте Mini App:",
        "empty_inv": "📦 Инвентарь пуст. Откройте кейс!",
        "bal_msg": "⭐ Ваш баланс: <b>{stars} ⭐</b>",
        "no_stars": "Недостаточно звёзд! Нужно {price} ⭐",
        "sold": "✅ Продано за <b>+{earned} ⭐</b> | Баланс: <b>{bal} ⭐</b>",
        "wd_ok": "📤 Заявка <b>#{wid}</b> на <b>{item}</b> ({nick}) создана.",
        "promo_used": "⚠️ Промокод уже использован.",
        "promo_ok": "🎉 Промокод активирован: <b>+{bonus} ⭐</b> | Баланс: <b>{bal} ⭐</b>",
    },
}

CASES: Dict[str, Dict[str, Any]] = {
    "daily24": {"title": "Daily Drop", "badge": "FREE 24H", "price": 0, "items": [
        {"name": "B-Day Candle", "rarity": "Common", "value": 20, "chance": 48},
        {"name": "Homemade Cake", "rarity": "Common", "value": 45, "chance": 34},
        {"name": "Santa Hat", "rarity": "Rare", "value": 80, "chance": 18},
    ]},
    "farm_box": {"title": "Farm Vault", "badge": "FARM", "price": 50, "items": [
        {"name": "Homemade Cake", "rarity": "Common", "value": 35, "chance": 48},
        {"name": "Loot Bag", "rarity": "Rare", "value": 70, "chance": 34},
        {"name": "Victory Medal", "rarity": "Rare", "value": 120, "chance": 18},
    ]},
    "lite_nft": {"title": "Lite Collectibles", "badge": "LITE", "price": 100, "items": [
        {"name": "Victory Medal", "rarity": "Rare", "value": 85, "chance": 46},
        {"name": "Scared Cat", "rarity": "Rare", "value": 165, "chance": 34},
        {"name": "Artisan Brick", "rarity": "Epic", "value": 280, "chance": 20},
    ]},
    "dubai_nft": {"title": "Дубай", "badge": "DUBAI", "price": 250, "items": [
        {"name": "Artisan Brick", "rarity": "Epic", "value": 210, "chance": 45},
        {"name": "Precious Peach", "rarity": "Epic", "value": 420, "chance": 35},
        {"name": "Durov's Cap", "rarity": "Mythic", "value": 780, "chance": 20},
    ]},
    "tg_originals": {"title": "Telegram Originals", "badge": "ORIGINALS", "price": 500, "items": [
        {"name": "Scared Cat", "rarity": "Rare", "value": 360, "chance": 45},
        {"name": "Astral Shard", "rarity": "Epic", "value": 740, "chance": 35},
        {"name": "Resistance Dog", "rarity": "Mythic", "value": 1350, "chance": 20},
    ]},
    "pepe_club": {"title": "Pepe Syndicate", "badge": "PEPE CLUB", "price": 800, "items": [
        {"name": "Precious Peach", "rarity": "Epic", "value": 620, "chance": 45},
        {"name": "Heart Locket", "rarity": "Mythic", "value": 1250, "chance": 35},
        {"name": "Plush Pepe", "rarity": "Legendary", "value": 2400, "chance": 20},
    ]},
    "king_vault": {"title": "XAVRR King", "badge": "KING VAULT", "price": 1500, "items": [
        {"name": "Astral Shard", "rarity": "Epic", "value": 1150, "chance": 45},
        {"name": "Durov's Cap", "rarity": "Mythic", "value": 2300, "chance": 35},
        {"name": "Plush Pepe", "rarity": "Legendary", "value": 4500, "chance": 20},
    ]},
    "mythic_crown": {"title": "Mythic Crown", "badge": "MYTHIC VIP", "price": 2500, "items": [
        {"name": "Resistance Dog", "rarity": "Mythic", "value": 1950, "chance": 45},
        {"name": "Heart Locket", "rarity": "Mythic", "value": 3800, "chance": 35},
        {"name": "Plush Pepe", "rarity": "Legendary", "value": 7500, "chance": 20},
    ]},
}

STAR_PACKS: Dict[str, int] = {"pack_100": 100, "pack_500": 500, "pack_1500": 1500}
PROMO_CODES: Dict[str, int] = {"XAVRR": 500, "KING": 250, "START": 150}


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, "
                "stars INTEGER NOT NULL DEFAULT 1000, lang TEXT NOT NULL DEFAULT 'uk', "
                "referrer_id INTEGER, created_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS inventory ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
                "item_name TEXT NOT NULL, rarity TEXT NOT NULL, value INTEGER NOT NULL, "
                "serial TEXT NOT NULL DEFAULT '#100', status TEXT NOT NULL DEFAULT 'inventory', "
                "created_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS used_promos ("
                "user_id INTEGER NOT NULL, code TEXT NOT NULL, PRIMARY KEY (user_id, code))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS withdrawals ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, "
                "username_tg TEXT NOT NULL, inventory_id INTEGER NOT NULL, "
                "item_name TEXT NOT NULL, value INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
                "created_at TEXT NOT NULL)"
            )

    def ensure_user(self, user_id: int, username: Optional[str], first_name: Optional[str], referrer_id: Optional[int] = None) -> sqlite3.Row:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                conn.execute("UPDATE users SET username = ?, first_name = ? WHERE user_id = ?", (username, first_name, user_id))
                return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            valid_ref = referrer_id if referrer_id and referrer_id != user_id and conn.execute("SELECT 1 FROM users WHERE user_id = ?", (referrer_id,)).fetchone() else None
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, stars, lang, referrer_id, created_at) VALUES (?, ?, ?, 1000, 'uk', ?, ?)",
                (user_id, username, first_name, valid_ref, now),
            )
            if valid_ref:
                conn.execute("UPDATE users SET stars = stars + 200 WHERE user_id = ?", (valid_ref,))
            return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def set_lang(self, user_id: int, lang: str) -> None:
        if lang not in TEXTS:
            return
        with self._connect() as conn:
            conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))

    def add_stars(self, user_id: int, delta: int) -> int:
        with self._connect() as conn:
            conn.execute("UPDATE users SET stars = MAX(0, stars + ?) WHERE user_id = ?", (delta, user_id))
            row = conn.execute("SELECT stars FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return int(row["stars"]) if row else 0

    def add_item(self, user_id: int, item: Dict[str, Any], serial: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO inventory (user_id, item_name, rarity, value, serial, status, created_at) VALUES (?, ?, ?, ?, ?, 'inventory', ?)",
                (user_id, item["name"], item.get("rarity", "Rare"), int(item["value"]), serial, now),
            )
            return int(cur.lastrowid)

    def get_inventory(self, user_id: int) -> List[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM inventory WHERE user_id = ? AND status = 'inventory' ORDER BY id DESC", (user_id,)).fetchall()

    def sell_item(self, user_id: int, item_id: int) -> Optional[int]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM inventory WHERE id = ? AND user_id = ? AND status = 'inventory'", (item_id, user_id)).fetchone()
            if not row:
                return None
            val = int(row["value"])
            conn.execute("UPDATE inventory SET status = 'sold' WHERE id = ?", (item_id,))
            conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (val, user_id))
            return val

    def create_withdrawal(self, user_id: int, item_id: int, username_tg: str) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM inventory WHERE id = ? AND user_id = ? AND status = 'inventory'", (item_id, user_id)).fetchone()
            if not row:
                return None
            conn.execute("UPDATE inventory SET status = 'withdrawing' WHERE id = ?", (item_id,))
            label = f"{row['item_name']} {row['serial']}"
            cur = conn.execute(
                "INSERT INTO withdrawals (user_id, username_tg, inventory_id, item_name, value, status, created_at) VALUES (?, ?, ?, ?, ?, 'pending', ?)",
                (user_id, username_tg, item_id, label, int(row["value"]), now),
            )
            return {"wid": int(cur.lastrowid), "item_name": label, "value": int(row["value"]), "username_tg": username_tg}

    def apply_promo(self, user_id: int, code: str) -> Optional[int]:
        up = code.strip().upper()
        bonus = PROMO_CODES.get(up)
        if not bonus:
            return None
        with self._connect() as conn:
            if conn.execute("SELECT 1 FROM used_promos WHERE user_id = ? AND code = ?", (user_id, up)).fetchone():
                return -1
            conn.execute("INSERT INTO used_promos (user_id, code) VALUES (?, ?)", (user_id, up))
            conn.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (bonus, user_id))
            return bonus


db = Database(DB_PATH)
router = Router()


def get_lang(user: sqlite3.Row) -> str:
    return user["lang"] if "lang" in user.keys() and user["lang"] in TEXTS else "uk"


def tr(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["uk"]).get(key, TEXTS["uk"].get(key, ""))


def main_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=tr(lang, "open_app"), web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton(text=tr(lang, "cases")), KeyboardButton(text=tr(lang, "inv"))],
            [KeyboardButton(text=tr(lang, "topup")), KeyboardButton(text=tr(lang, "lang_btn"))],
        ],
        resize_keyboard=True,
    )


def lang_inline_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇦 UK", callback_data="lang:uk"),
        InlineKeyboardButton(text="🇬🇧 EN", callback_data="lang:en"),
        InlineKeyboardButton(text="🇷🇺 RU", callback_data="lang:ru"),
    ]])


def cases_inline_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"[{c['badge']}] {c['title']} — {c['price']} ⭐", callback_data=f"case:{cid}")] for cid, c in CASES.items()]
    rows.append([InlineKeyboardButton(text=tr(lang, "open_app"), web_app=WebAppInfo(url=WEBAPP_URL))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pick_weighted(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = sum(int(i["chance"]) for i in items)
    roll = random.uniform(0, total)
    acc = 0.0
    for it in items:
        acc += float(it["chance"])
        if roll <= acc:
            return it
    return items[-1]


def make_serial() -> str:
    return f"#{random.randint(10, 4999)}"


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    if not message.from_user:
        return
    ref_id: Optional[int] = None
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("ref_") and parts[1][4:].isdigit():
            ref_id = int(parts[1][4:])
    user = db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name, ref_id)
    lang = get_lang(user)
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{message.from_user.id}"
    await message.answer(
        tr(lang, "start").format(
            name=message.from_user.first_name or "Player",
            uid=message.from_user.id,
            stars=user["stars"],
            ref=ref_link,
        ),
        reply_markup=main_kb(lang),
    )


@router.message(Command("lang"))
@router.message(F.text.in_({"🌐 Мова / Language", "🌐 Language", "🌐 Язык"}))
async def cmd_lang(message: Message) -> None:
    if not message.from_user:
        return
    user = db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(tr(get_lang(user), "choose_lang"), reply_markup=lang_inline_kb())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        return
    lang = callback.data.split(":", 1)[1]
    if lang not in TEXTS:
        return
    db.set_lang(callback.from_user.id, lang)
    await callback.answer("OK")
    await callback.message.answer(tr(lang, "lang_set"), reply_markup=main_kb(lang))


@router.message(F.text.in_({"🎁 Кейси", "🎁 Cases", "🎁 Кейсы"}))
async def msg_cases(message: Message) -> None:
    if not message.from_user:
        return
    user = db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    lang = get_lang(user)
    await message.answer(tr(lang, "cases_hdr"), reply_markup=cases_inline_kb(lang))


@router.callback_query(F.data.startswith("case:"))
async def cb_case(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        return
    cid = callback.data.split(":", 1)[1]
    case = CASES.get(cid)
    if not case:
        return
    user = db.ensure_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    lang = get_lang(user)
    price = int(case["price"])
    if int(user["stars"]) < price:
        await callback.answer(tr(lang, "no_stars").format(price=price), show_alert=True)
        return
    db.add_stars(callback.from_user.id, -price)
    won = pick_weighted(case["items"])
    serial = make_serial()
    inv_id = db.add_item(callback.from_user.id, won, serial)
    bal = db.add_stars(callback.from_user.id, 0)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"+{won['value']} ⭐", callback_data=f"sell:{inv_id}"), InlineKeyboardButton(text="📤", callback_data=f"wd:{inv_id}")],
        [InlineKeyboardButton(text="🔁", callback_data=f"case:{cid}")],
    ])
    await callback.answer("OK")
    await callback.message.answer(f"<b>[{case['badge']}] {case['title']}</b>\nNFT: <b>{won['name']}</b> <code>{serial}</code> ({won['value']} ⭐)\n⭐ <b>{bal}</b>", reply_markup=kb)


@router.callback_query(F.data.startswith("sell:"))
async def cb_sell(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        return
    user = db.ensure_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    lang = get_lang(user)
    earned = db.sell_item(callback.from_user.id, int(callback.data.split(":", 1)[1]))
    if earned is None:
        return
    bal = db.add_stars(callback.from_user.id, 0)
    await callback.answer(f"+{earned} ⭐")
    await callback.message.edit_text(tr(lang, "sold").format(earned=earned, bal=bal))


@router.callback_query(F.data.startswith("wd:"))
async def cb_wd(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        return
    user = db.ensure_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    lang = get_lang(user)
    nick = f"@{callback.from_user.username}" if callback.from_user.username else f"id:{callback.from_user.id}"
    res = db.create_withdrawal(callback.from_user.id, int(callback.data.split(":", 1)[1]), nick)
    if not res:
        return
    await callback.answer("OK")
    await callback.message.edit_text(tr(lang, "wd_ok").format(wid=res["wid"], item=res["item_name"], nick=nick))
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, f"🔔 #{res['wid']} {nick}: <b>{res['item_name']}</b> ({res['value']} ⭐)")
        except Exception:
            logger.exception("Admin notify error")


@router.message(F.text.in_({"📦 Інвентар", "📦 Inventory", "📦 Инвентарь"}))
async def msg_inv(message: Message) -> None:
    if not message.from_user:
        return
    user = db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    lang = get_lang(user)
    items = db.get_inventory(message.from_user.id)
    if not items:
        await message.answer(tr(lang, "empty_inv"))
        return
    lines = [f"• <b>{r['item_name']}</b> <code>{r['serial']}</code> — {r['value']} ⭐" for r in items[:10]]
    btns = [[InlineKeyboardButton(text=f"+{r['value']} ⭐", callback_data=f"sell:{r['id']}"), InlineKeyboardButton(text="📤", callback_data=f"wd:{r['id']}")] for r in items[:10]]
    await message.answer("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.message(F.text.in_({"⭐ Баланс / Поповнити", "⭐ Balance / Top up", "⭐ Баланс / Пополнить"}))
async def msg_bal(message: Message) -> None:
    if not message.from_user:
        return
    user = db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    lang = get_lang(user)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="+100 ⭐", callback_data="buy:pack_100"), InlineKeyboardButton(text="+500 ⭐", callback_data="buy:pack_500"), InlineKeyboardButton(text="+1500 ⭐", callback_data="buy:pack_1500")],
        [InlineKeyboardButton(text=tr(lang, "open_app"), web_app=WebAppInfo(url=WEBAPP_URL))],
    ])
    await message.answer(tr(lang, "bal_msg").format(stars=user["stars"]), reply_markup=kb)


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery) -> None:
    if not callback.data or not callback.message:
        return
    amt = STAR_PACKS.get(callback.data.split(":", 1)[1])
    if not amt:
        return
    await callback.answer()
    await callback.message.answer_invoice(title=f"{amt} ⭐ — XAVRR GIFT", description=f"+{amt} ⭐", payload=f"stars:{amt}", currency="XTR", prices=[LabeledPrice(label=f"{amt} ⭐", amount=amt)])


@router.pre_checkout_query()
async def on_pre_checkout(q: PreCheckoutQuery) -> None:
    await q.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message) -> None:
    if not message.from_user or not message.successful_payment:
        return
    p = message.successful_payment.invoice_payload or ""
    if p.startswith("stars:"):
        amt = int(p.split(":", 1)[1])
        bal = db.add_stars(message.from_user.id, amt)
        await message.answer(f"✅ +{amt} ⭐ | ⭐ <b>{bal}</b>")


@router.message(F.web_app_data)
async def on_wa(message: Message) -> None:
    if not message.from_user or not message.web_app_data:
        return
    try:
        data = json.loads(message.web_app_data.data)
    except Exception:
        data = {}
    if data.get("action") == "withdraw":
        await message.answer(f"📤 <b>{data.get('item_name')}</b> ({data.get('value')} 💎)")


@router.message(F.text)
async def on_text(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    user = db.ensure_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    lang = get_lang(user)
    up = message.text.strip().upper()
    if up in PROMO_CODES:
        res = db.apply_promo(message.from_user.id, up)
        if res == -1:
            await message.answer(tr(lang, "promo_used"))
        elif res:
            bal = db.add_stars(message.from_user.id, 0)
            await message.answer(tr(lang, "promo_ok").format(bonus=res, bal=bal))
        return
    await message.answer(tr(lang, "open_app"), reply_markup=main_kb(lang))


async def start_web() -> None:
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="OK"))
    app.router.add_get("/health", lambda r: web.Response(text="OK"))
    wa_dir = Path(__file__).resolve().parent / "webapp"
    if wa_dir.is_dir():
        app.router.add_static("/webapp/", path=str(wa_dir), name="webapp")
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=PORT).start()


async def main() -> None:
    await start_web()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
