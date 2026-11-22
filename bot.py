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
from aiogram.filters import CommandStart
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
    raise RuntimeError("Вкажи BOT_TOKEN у змінних середовища або у файлі .env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("xavrr_gift_bot")

CASES: Dict[str, Dict[str, Any]] = {
    "farm": {
        "id": "farm",
        "tag": "ФАРМ",
        "emoji": "🌾",
        "title": "Фарм Кейс",
        "price": 50,
        "items": [
            {"name": "B-Day Candle", "rarity": "common", "value": 25, "chance": 50, "emoji": "🕯️"},
            {"name": "Santa Hat", "rarity": "common", "value": 45, "chance": 35, "emoji": "🎅"},
            {"name": "Homemade Cake", "rarity": "rare", "value": 85, "chance": 15, "emoji": "🎂"},
        ],
    },
    "small": {
        "id": "small",
        "tag": "МЄЛОЧ",
        "emoji": "🪙",
        "title": "Мєлоч Кейс",
        "price": 100,
        "items": [
            {"name": "Homemade Cake", "rarity": "common", "value": 70, "chance": 48, "emoji": "🎂"},
            {"name": "Ice Cream", "rarity": "rare", "value": 120, "chance": 34, "emoji": "🍨"},
            {"name": "Loot Bag", "rarity": "epic", "value": 210, "chance": 18, "emoji": "🎒"},
        ],
    },
    "rare": {
        "id": "rare",
        "tag": "РІДКІСНІ",
        "emoji": "💠",
        "title": "Рідкісні NFT",
        "price": 250,
        "items": [
            {"name": "Victory Medal", "rarity": "rare", "value": 180, "chance": 45, "emoji": "🏅"},
            {"name": "Scared Cat", "rarity": "epic", "value": 390, "chance": 35, "emoji": "🐱"},
            {"name": "Artisan Brick", "rarity": "legendary", "value": 640, "chance": 20, "emoji": "🧱"},
        ],
    },
    "dubai": {
        "id": "dubai",
        "tag": "ДУБАЙ",
        "emoji": "🏙️",
        "title": "Дубай",
        "price": 500,
        "items": [
            {"name": "Artisan Brick", "rarity": "rare", "value": 420, "chance": 45, "emoji": "🧱"},
            {"name": "Precious Peach", "rarity": "epic", "value": 780, "chance": 35, "emoji": "🍑"},
            {"name": "Durov's Cap", "rarity": "mythic", "value": 1450, "chance": 20, "emoji": "🧢"},
        ],
    },
    "premium": {
        "id": "premium",
        "tag": "ПРЕМІУМ",
        "emoji": "👑",
        "title": "Преміум Кейс",
        "price": 1000,
        "items": [
            {"name": "Heroic Helmet", "rarity": "epic", "value": 850, "chance": 45, "emoji": "⛑️"},
            {"name": "Astral Shard", "rarity": "legendary", "value": 1500, "chance": 35, "emoji": "🔮"},
            {"name": "Resistance Dog", "rarity": "mythic", "value": 2600, "chance": 20, "emoji": "🐕"},
        ],
    },
    "vip": {
        "id": "vip",
        "tag": "VIP",
        "emoji": "💎",
        "title": "VIP Кейс",
        "price": 2500,
        "items": [
            {"name": "Durov's Cap", "rarity": "legendary", "value": 2100, "chance": 48, "emoji": "🧢"},
            {"name": "Heart Locket", "rarity": "mythic", "value": 3800, "chance": 34, "emoji": "💖"},
            {"name": "Plush Pepe", "rarity": "mythic", "value": 7500, "chance": 18, "emoji": "🐸"},
        ],
    },
}

STAR_PACKS: Dict[str, int] = {
    "pack_100": 100,
    "pack_500": 500,
    "pack_1500": 1500,
}

PROMO_CODES: Dict[str, int] = {
    "XAVRR": 500,
    "KING": 250,
    "START": 150,
}


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
                "user_id INTEGER PRIMARY KEY, "
                "username TEXT, "
                "first_name TEXT, "
                "stars INTEGER NOT NULL DEFAULT 1000, "
                "referrer_id INTEGER, "
                "created_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS inventory ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "user_id INTEGER NOT NULL, "
                "item_name TEXT NOT NULL, "
                "rarity TEXT NOT NULL, "
                "value INTEGER NOT NULL, "
                "emoji TEXT NOT NULL, "
                "status TEXT NOT NULL DEFAULT 'inventory', "
                "created_at TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS used_promos ("
                "user_id INTEGER NOT NULL, "
                "code TEXT NOT NULL, "
                "PRIMARY KEY (user_id, code))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS withdrawals ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "user_id INTEGER NOT NULL, "
                "username_tg TEXT NOT NULL, "
                "inventory_id INTEGER NOT NULL, "
                "item_name TEXT NOT NULL, "
                "value INTEGER NOT NULL, "
                "status TEXT NOT NULL DEFAULT 'pending', "
                "created_at TEXT NOT NULL)"
            )

    def ensure_user(
        self,
        user_id: int,
        username: Optional[str],
        first_name: Optional[str],
        referrer_id: Optional[int] = None,
    ) -> sqlite3.Row:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                    (username, first_name, user_id),
                )
                return conn.execute(
                    "SELECT * FROM users WHERE user_id = ?", (user_id,)
                ).fetchone()

            valid_ref = (
                referrer_id
                if referrer_id
                and referrer_id != user_id
                and conn.execute(
                    "SELECT 1 FROM users WHERE user_id = ?", (referrer_id,)
                ).fetchone()
                else None
            )
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, stars, referrer_id, created_at) "
                "VALUES (?, ?, ?, 1000, ?, ?)",
                (user_id, username, first_name, valid_ref, now),
            )
            if valid_ref:
                conn.execute(
                    "UPDATE users SET stars = stars + 200 WHERE user_id = ?",
                    (valid_ref,),
                )
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()

    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()

    def add_stars(self, user_id: int, delta: int) -> int:
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET stars = MAX(0, stars + ?) WHERE user_id = ?",
                (delta, user_id),
            )
            row = conn.execute(
                "SELECT stars FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return int(row["stars"]) if row else 0

    def add_inventory_item(self, user_id: int, item: Dict[str, Any]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO inventory (user_id, item_name, rarity, value, emoji, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'inventory', ?)",
                (
                    user_id,
                    item["name"],
                    item["rarity"],
                    int(item["value"]),
                    item.get("emoji", "🎁"),
                    now,
                ),
            )
            return int(cur.lastrowid)

    def get_inventory(self, user_id: int) -> List[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                "SELECT * FROM inventory "
                "WHERE user_id = ? AND status = 'inventory' "
                "ORDER BY id DESC",
                (user_id,),
            ).fetchall()

    def sell_item(self, user_id: int, item_id: int) -> Optional[int]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM inventory "
                "WHERE id = ? AND user_id = ? AND status = 'inventory'",
                (item_id, user_id),
            ).fetchone()
            if not row:
                return None
            val = int(row["value"])
            conn.execute(
                "UPDATE inventory SET status = 'sold' WHERE id = ?", (item_id,)
            )
            conn.execute(
                "UPDATE users SET stars = stars + ? WHERE user_id = ?",
                (val, user_id),
            )
            return val

    def create_withdrawal(
        self, user_id: int, item_id: int, username_tg: str
    ) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM inventory "
                "WHERE id = ? AND user_id = ? AND status = 'inventory'",
                (item_id, user_id),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                "UPDATE inventory SET status = 'withdrawing' WHERE id = ?",
                (item_id,),
            )
            cur = conn.execute(
                "INSERT INTO withdrawals (user_id, username_tg, inventory_id, item_name, value, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
                (
                    user_id,
                    username_tg,
                    item_id,
                    row["item_name"],
                    int(row["value"]),
                    now,
                ),
            )
            return {
                "withdrawal_id": int(cur.lastrowid),
                "item_name": row["item_name"],
                "value": int(row["value"]),
                "username_tg": username_tg,
            }

    def apply_promo(self, user_id: int, code: str) -> Optional[int]:
        normalized = code.strip().upper()
        bonus = PROMO_CODES.get(normalized)
        if not bonus:
            return None
        with self._connect() as conn:
            already = conn.execute(
                "SELECT 1 FROM used_promos WHERE user_id = ? AND code = ?",
                (user_id, normalized),
            ).fetchone()
            if already:
                return -1
            conn.execute(
                "INSERT INTO used_promos (user_id, code) VALUES (?, ?)",
                (user_id, normalized),
            )
            conn.execute(
                "UPDATE users SET stars = stars + ? WHERE user_id = ?",
                (bonus, user_id),
            )
            return bonus

    def count_referrals(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM users WHERE referrer_id = ?",
                (user_id,),
            ).fetchone()
            return int(row["cnt"]) if row else 0


db = Database(DB_PATH)
router = Router()


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="👑 Відкрити XAVRR GIFT",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ],
            [KeyboardButton(text="🎁 Кейси"), KeyboardButton(text="🎒 Інвентар")],
            [
                KeyboardButton(text="⭐ Баланс / Поповнити"),
                KeyboardButton(text="👥 Реферали та Промо"),
            ],
        ],
        resize_keyboard=True,
    )


def cases_keyboard() -> InlineKeyboardMarkup:
    order = ["farm", "small", "rare", "dubai", "premium", "vip"]
    rows = [
        [
            InlineKeyboardButton(
                text=f"[{CASES[cid]['tag']}] {CASES[cid]['emoji']} {CASES[cid]['title']} — {CASES[cid]['price']} ⭐",
                callback_data=f"case:{cid}",
            )
        ]
        for cid in order
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="🚀 Відкрити в Mini App",
                web_app=WebAppInfo(url=WEBAPP_URL),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="+100 ⭐", callback_data="buy:pack_100"),
                InlineKeyboardButton(text="+500 ⭐", callback_data="buy:pack_500"),
                InlineKeyboardButton(text="+1500 ⭐", callback_data="buy:pack_1500"),
            ],
            [
                InlineKeyboardButton(
                    text="📱 Поповнити у Mini App",
                    web_app=WebAppInfo(url=WEBAPP_URL),
                )
            ],
        ]
    )


def pick_weighted_item(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = sum(int(i["chance"]) for i in items)
    roll = random.uniform(0, total)
    acc = 0.0
    for item in items:
        acc += float(item["chance"])
        if roll <= acc:
            return item
    return items[-1]


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    if not message.from_user:
        return
    ref_id: Optional[int] = None
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) == 2 and parts[1].startswith("ref_"):
            raw_id = parts[1].removeprefix("ref_")
            if raw_id.isdigit():
                ref_id = int(raw_id)

    user = db.ensure_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        referrer_id=ref_id,
    )
    bot_me = await bot.get_me()
    ref_link = f"https://t.me/{bot_me.username}?start=ref_{message.from_user.id}"

    await message.answer(
        f"👑 <b>XAVRR GIFT</b> — кейси та колекційні подарунки / NFT у Telegram.\n\n"
        f"Вітаємо, <b>{message.from_user.first_name or 'Гравець'}</b>!\n"
        f"⭐ Баланс: <b>{user['stars']} зірок</b>\n"
        f"🎟 Промокод на старт: <code>XAVRR</code> (+500 ⭐)\n"
        f"🔗 Ваше реферальне посилання:\n<code>{ref_link}</code>",
        reply_markup=main_reply_keyboard(),
    )


@router.message(F.text == "🎁 Кейси")
async def msg_cases(message: Message) -> None:
    await message.answer(
        "🎁 <b>Обери кейс (Фарм, Мєлоч, Рідкісні, Дубай, Преміум, VIP) або запусти Mini App:</b>",
        reply_markup=cases_keyboard(),
    )


@router.callback_query(F.data.startswith("case:"))
async def cb_open_case(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        return
    cid = callback.data.split(":", 1)[1]
    case = CASES.get(cid)
    if not case:
        await callback.answer("Кейс не знайдено", show_alert=True)
        return

    user = db.ensure_user(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.first_name,
    )
    price = int(case["price"])
    if int(user["stars"]) < price:
        await callback.answer(
            f"Недостатньо зірок! Потрібно {price} ⭐", show_alert=True
        )
        return

    db.add_stars(callback.from_user.id, -price)
    won = pick_weighted_item(case["items"])
    inv_id = db.add_inventory_item(callback.from_user.id, won)
    new_balance = db.get_user(callback.from_user.id)["stars"]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💰 Продати за +{won['value']} ⭐",
                    callback_data=f"sell:{inv_id}",
                ),
                InlineKeyboardButton(
                    text="📤 Вивести NFT",
                    callback_data=f"withdraw:{inv_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔁 Відкрити ще раз",
                    callback_data=f"case:{cid}",
                )
            ],
        ]
    )

    await callback.answer("Кейс відкрито!")
    await callback.message.answer(
        f"{won['emoji']} Ви відкрили <b>[{case['tag']}] {case['title']}</b>!\n"
        f"Випало: <b>{won['name']}</b> (цінність: <b>{won['value']} ⭐</b>)\n"
        f"Залишок балансу: <b>{new_balance} ⭐</b>",
        reply_markup=kb,
    )


@router.callback_query(F.data.startswith("sell:"))
async def cb_sell_item(callback: CallbackQuery) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        return
    item_id = int(callback.data.split(":", 1)[1])
    earned = db.sell_item(callback.from_user.id, item_id)
    if earned is None:
        await callback.answer("Предмет уже продано або недоступний", show_alert=True)
        return
    bal = db.get_user(callback.from_user.id)["stars"]
    await callback.answer(f"+{earned} ⭐ нараховано!")
    await callback.message.edit_text(
        f"✅ Предмет продано за <b>+{earned} ⭐</b>.\n"
        f"Поточний баланс: <b>{bal} ⭐</b>"
    )


@router.callback_query(F.data.startswith("withdraw:"))
async def cb_withdraw_item(callback: CallbackQuery, bot: Bot) -> None:
    if not callback.from_user or not callback.data or not callback.message:
        return
    item_id = int(callback.data.split(":", 1)[1])
    tg_nick = (
        f"@{callback.from_user.username}"
        if callback.from_user.username
        else f"id:{callback.from_user.id}"
    )
    res = db.create_withdrawal(callback.from_user.id, item_id, tg_nick)
    if not res:
        await callback.answer("Предмет уже оброблено", show_alert=True)
        return

    await callback.answer("Заявку створено!")
    await callback.message.edit_text(
        f"📤 Заявка <b>#{res['withdrawal_id']}</b> на вивід <b>{res['item_name']}</b> "
        f"на акаунт <b>{tg_nick}</b> передана в обробку."
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔔 Нова заявка на вивід #{res['withdrawal_id']}\n"
                f"Користувач: {tg_nick} (<code>{callback.from_user.id}</code>)\n"
                f"Приз: <b>{res['item_name']}</b> ({res['value']} ⭐)",
            )
        except Exception:
            logger.exception("Не вдалося сповістити адміна %s", admin_id)


@router.message(F.text == "🎒 Інвентар")
async def msg_inventory(message: Message) -> None:
    if not message.from_user:
        return
    items = db.get_inventory(message.from_user.id)
    if not items:
        await message.answer(
            "🎒 Ваш інвентар поки порожній. Відкрийте кейс!",
            reply_markup=cases_keyboard(),
        )
        return

    lines = ["🎒 <b>Ваш інвентар:</b>\n"]
    buttons: List[List[InlineKeyboardButton]] = []
    for row in items[:10]:
        lines.append(
            f"• {row['emoji']} <b>{row['item_name']}</b> — {row['value']} ⭐"
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"💰 Продати ({row['value']} ⭐)",
                    callback_data=f"sell:{row['id']}",
                ),
                InlineKeyboardButton(
                    text=f"📤 Вивести #{row['id']}",
                    callback_data=f"withdraw:{row['id']}",
                ),
            ]
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.message(F.text == "⭐ Баланс / Поповнити")
async def msg_balance(message: Message) -> None:
    if not message.from_user:
        return
    user = db.ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )
    await message.answer(
        f"⭐ Ваш баланс: <b>{user['stars']} зірок</b>\n\n"
        f"Оберіть пакет поповнення через Telegram Stars:",
        reply_markup=topup_keyboard(),
    )


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy_stars(callback: CallbackQuery) -> None:
    if not callback.data or not callback.message:
        return
    pack_key = callback.data.split(":", 1)[1]
    amount = STAR_PACKS.get(pack_key)
    if not amount:
        await callback.answer("Пакет не знайдено", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer_invoice(
        title=f"Пакет {amount} ⭐ — XAVRR GIFT",
        description=f"Нарахування {amount} ігрових зірок на баланс у XAVRR GIFT.",
        payload=f"stars:{amount}",
        currency="XTR",
        prices=[LabeledPrice(label=f"{amount} зірок", amount=amount)],
    )


@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message) -> None:
    if not message.from_user or not message.successful_payment:
        return
    payload = message.successful_payment.invoice_payload or ""
    if payload.startswith("stars:"):
        try:
            amount = int(payload.split(":", 1)[1])
        except ValueError:
            amount = 0
        if amount > 0:
            new_bal = db.add_stars(message.from_user.id, amount)
            await message.answer(
                f"✅ Оплата пройшла успішно! Нараховано <b>+{amount} ⭐</b>.\n"
                f"Новий баланс: <b>{new_bal} ⭐</b>"
            )


@router.message(F.text == "👥 Реферали та Промо")
async def msg_referrals_promo(message: Message, bot: Bot) -> None:
    if not message.from_user:
        return
    bot_me = await bot.get_me()
    ref_link = f"https://t.me/{bot_me.username}?start=ref_{message.from_user.id}"
    refs_count = db.count_referrals(message.from_user.id)
    await message.answer(
        f"👥 Запрошено друзів: <b>{refs_count}</b> (+200 ⭐ за кожного)\n"
        f"🔗 Ваше посилання:\n<code>{ref_link}</code>\n\n"
        f"🎟 Щоб активувати промокод (наприклад, <code>XAVRR</code>), просто надішліть його повідомленням у чат!",
    )


@router.message(F.web_app_data)
async def on_webapp_data(message: Message) -> None:
    if not message.from_user or not message.web_app_data:
        return
    raw = message.web_app_data.data
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw": raw}

    action = data.get("action")
    if action == "withdraw":
        item_name = str(data.get("item_name", "NFT Приз"))
        value = int(data.get("value", 0))
        tg_nick = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else f"id:{message.from_user.id}"
        )
        await message.answer(
            f"📤 Отримано запит із Mini App на вивід <b>{item_name}</b> ({value} ⭐) для <b>{tg_nick}</b>."
        )
    else:
        await message.answer(
            f"📲 Дані з Mini App синхронізовано: <code>{raw[:300]}</code>"
        )


@router.message(F.text)
async def on_promo_or_text(message: Message) -> None:
    if not message.from_user or not message.text:
        return
    text = message.text.strip()
    if text.upper() in PROMO_CODES:
        res = db.apply_promo(message.from_user.id, text)
        if res == -1:
            await message.answer("⚠️ Ви вже використовували цей промокод.")
        elif res:
            bal = db.get_user(message.from_user.id)["stars"]
            await message.answer(
                f"🎉 Промокод <b>{text.upper()}</b> активовано! Отримано <b>+{res} ⭐</b>.\n"
                f"Баланс: <b>{bal} ⭐</b>"
            )
        return

    await message.answer(
        "Оберіть дію на клавіатурі нижче або відкрийте <b>XAVRR GIFT</b>:",
        reply_markup=main_reply_keyboard(),
    )


async def start_health_server() -> None:
    async def health(request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    webapp_dir = Path(__file__).resolve().parent / "webapp"
    if webapp_dir.is_dir():
        app.router.add_static("/webapp/", path=str(webapp_dir), name="webapp")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info("HTTP сервер запущено на порту %s", PORT)


async def main() -> None:
    await start_health_server()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)
    logger.info("Запуск XAVRR GIFT бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
