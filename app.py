"""
╔══════════════════════════════════════════════════╗
║           NECROCIDE / HESITEY GIFT BOT           ║
╚══════════════════════════════════════════════════╝
"""

import asyncio
import random
import string
import os
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, Message
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiohttp import web

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ╔══════════════════════════════════════════════════╗
# ║                  КОНФИГУРАЦИЯ                   ║
# ╚══════════════════════════════════════════════════╝

BOT_TOKEN = os.environ["BOT_TOKEN"]

CHANNEL_1_ID   = -1003993803454
CHANNEL_2_ID   = -1003859905398
CHANNEL_1_LINK = "https://t.me/+_W1Hit0AXMExMzVi"
CHANNEL_2_LINK = "https://t.me/KultovHesitey"
CHANNEL_1_NAME = "🖤 NECROCIDE"
CHANNEL_2_NAME = "⚡️ ПЕРЕХОДНИК HESITEY"

ADMIN_IDS        = [8377328708, 995258854]
REQUIRED_INVITES = 7
CONTACT_USERNAME = "@FuckHesitey"

PHOTO_URL = (
    "https://i.postimg.cc/90Ryk33F/"
    "file-000000005fd87243ba6d7497f8878878.png"
)

PHOTO_30_STARS = "https://i.postimg.cc/FFfLQGQ0/file-000000000fb4720ab4f44e21c7bbcd1b.png"
PHOTO_3_MICE = "https://i.postimg.cc/pdq29NK2/file-00000000747871f4b211b4ef835ef2dd.png"
PHOTO_PROMO = "https://i.postimg.cc/7b8DvqrS/file-00000000e7b0720a8fe239d6055ca386.png"
PHOTO_REFERRALS = "https://i.postimg.cc/50rb3w7M/file-00000000ea40720aae282ec30eb5e488.png"
PHOTO_STATS = "https://i.postimg.cc/PfB8fZtB/file-000000008998720aa0c0b5ce2acfd496.png"

GIFTS = {
    "gift_30":   {"label": "💰 30 Звёзд", "emoji": "💰", "name": "30 Звёзд"},
    "gift_mice": {"label": "🧸 3 Мишки",  "emoji": "🧸", "name": "3 Мишки"},
}

# ╔══════════════════════════════════════════════════╗
# ║              ХРАНИЛИЩЕ ДАННЫХ                   ║
# ╚══════════════════════════════════════════════════╝

users: set          = set()
invites_count: dict = {}
pending_refs: dict  = {}
promocodes: dict    = {}
used_gifts: dict    = {}

stats = {
    "sub_checks":  0,
    "gift_clicks": {
        "gift_30":    0,
        "gift_mice":  0,
        "gift_promo": 0,
    },
    "promo_tries": 0,
    "promo_ok":    0,
    "total_refs":  0,
    "gifts_given": 0,
    "started_at":  datetime.now(),
}

# ╔══════════════════════════════════════════════════╗
# ║                   FSM СОСТОЯНИЯ                 ║
# ╚══════════════════════════════════════════════════╝

class AdminState(StatesGroup):
    promo_name        = State()
    promo_activations = State()
    promo_days        = State()

class UserState(StatesGroup):
    enter_promo = State()

# ╔══════════════════════════════════════════════════╗
# ║                    КЛАВИАТУРЫ                   ║
# ╚══════════════════════════════════════════════════╝

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰  30 Звёзд",        callback_data="gift_30")],
        [InlineKeyboardButton(text="🧸  3 Мишки",         callback_data="gift_mice")],
        [InlineKeyboardButton(text="🎟  Ввести промокод",  callback_data="gift_promo")],
        [InlineKeyboardButton(text="👥  Мои рефералы",    callback_data="referrals")],
    ])

def kb_subscribe() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=CHANNEL_1_NAME, url=CHANNEL_1_LINK)],
        [InlineKeyboardButton(text=CHANNEL_2_NAME, url=CHANNEL_2_LINK)],
        [InlineKeyboardButton(text="✅  Я подписался!", callback_data="check_sub")],
        [InlineKeyboardButton(text="◀️  Назад",         callback_data="back")],
    ])

def kb_referrals() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗  Моя реферальная ссылка", callback_data="get_link")],
        [InlineKeyboardButton(text="🔄  Обновить прогресс",      callback_data="check_refs")],
        [InlineKeyboardButton(text="◀️  Назад",                  callback_data="back")],
    ])

def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️  Назад", callback_data="back")],
    ])

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊  Статистика",        callback_data="adm_stats")],
        [InlineKeyboardButton(text="🆕  Создать промокод",  callback_data="adm_create")],
        [InlineKeyboardButton(text="📋  Список промокодов", callback_data="adm_list")],
        [InlineKeyboardButton(text="◀️  В главное меню",   callback_data="back")],
    ])

# ╔══════════════════════════════════════════════════╗
# ║               ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ           ║
# ╚══════════════════════════════════════════════════╝

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())


def html_escape(text: str) -> str:
    """Экранирует спецсимволы HTML чтобы имена пользователей не ломали разметку."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def get_username_line(user) -> str:
    """Возвращает @username или пометку об отсутствии."""
    if user.username:
        return f"@{html_escape(user.username)}"
    return "(нет username)"


async def is_subscribed(user_id: int, channel_id: int) -> bool:
    try:
        m = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return m.status in ("creator", "administrator", "member")
    except Exception:
        return False


async def bot_username() -> str:
    me = await bot.get_me()
    return me.username


def make_ref_link(username: str, user_id: int) -> str:
    return f"https://t.me/{username}?start={user_id}"


def gen_promo_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=10))


def progress_bar(done: int, total: int) -> str:
    done = min(done, total)
    return "🟩" * done + "⬜️" * (total - done)


def format_uptime() -> str:
    delta = datetime.now() - stats["started_at"]
    h, rem = divmod(int(delta.total_seconds()), 3600)
    m = rem // 60
    if h >= 24:
        d, h = divmod(h, 24)
        return f"{d}д {h}ч {m}м"
    return f"{h}ч {m}м"


async def safe_delete(msg: Message) -> None:
    try:
        await msg.delete()
    except TelegramBadRequest:
        pass


async def notify_admins(text: str) -> None:
    """Отправляет уведомление админам. Текст должен быть в формате HTML."""
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, text, parse_mode="HTML")
        except Exception:
            pass


async def show_main_menu(target: Message | CallbackQuery) -> None:
    caption = (
        "🎁 *Привет! Это звезды от Necrocide*\n\n"
        "Здесь ты можешь получить крутые подарки — "
        "звёзды, мишки или активировать промокод 🔥\n\n"
        "👇 *Выбери, что тебя интересует:*"
    )
    if isinstance(target, CallbackQuery):
        msg = target.message
        await safe_delete(msg)
        await bot.send_photo(
            chat_id=msg.chat.id,
            photo=PHOTO_URL,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )
    else:
        await target.answer_photo(
            photo=PHOTO_URL,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )

# ╔══════════════════════════════════════════════════╗
# ║                    КОМАНДЫ                      ║
# ╚══════════════════════════════════════════════════╝

@dp.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    user_id = msg.from_user.id
    users.add(user_id)

    parts = msg.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        referrer_id = int(parts[1])
        if referrer_id != user_id and user_id not in pending_refs and user_id not in used_gifts:
            pending_refs[user_id] = referrer_id
            await msg.answer_photo(
                photo=PHOTO_REFERRALS,
                caption=(
                    "👋 *Привет! Ты пришёл по реферальной ссылке*\n\n"
                    "Чтобы твой друг получил +1 к прогрессу, "
                    "сделай два простых шага:\n\n"
                    "1️⃣  Подпишись на оба канала\n"
                    "2️⃣  Нажми кнопку *«Я подписался!»* в меню\n\n"
                    "После этого реферал засчитается автоматически 🤝"
                ),
                parse_mode="Markdown",
            )

    await show_main_menu(msg)


@dp.message(Command("admin"))
async def cmd_admin(msg: Message) -> None:
    if msg.from_user.id not in ADMIN_IDS:
        await msg.answer("❌ Нет доступа.")
        return
    await msg.answer_photo(
        photo=PHOTO_STATS,
        caption="🛡 *Админ-панель*\n\nВыбери действие:",
        parse_mode="Markdown",
        reply_markup=kb_admin(),
    )


@dp.message(Command("cancel"))
async def cmd_cancel(msg: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current:
        await state.clear()
        await msg.answer_photo(
            photo=PHOTO_URL,
            caption="❌ *Действие отменено*",
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )
    else:
        await msg.answer("Нечего отменять 🤷", reply_markup=kb_main())

# ╔══════════════════════════════════════════════════╗
# ║              ГЛАВНОЕ МЕНЮ — КОЛБЭКИ             ║
# ╚══════════════════════════════════════════════════╝

@dp.callback_query(F.data == "back")
async def cb_back(cb: CallbackQuery, state: FSMContext) -> None:
    users.add(cb.from_user.id)
    await state.clear()
    await cb.answer()
    await show_main_menu(cb)


@dp.callback_query(F.data.in_({"gift_30", "gift_mice"}))
async def cb_gift(cb: CallbackQuery, state: FSMContext) -> None:
    user_id  = cb.from_user.id
    users.add(user_id)
    gift_key = cb.data
    stats["gift_clicks"][gift_key] += 1

    if user_id in used_gifts:
        await cb.answer(
            f"❌ Ты уже получил: {used_gifts[user_id]}",
            show_alert=True,
        )
        return

    await state.update_data(selected_gift=gift_key)
    await cb.answer()
    await safe_delete(cb.message)
    
    # Выбираем фото в зависимости от подарка
    photo = PHOTO_30_STARS if gift_key == "gift_30" else PHOTO_3_MICE
    
    await cb.message.answer_photo(
        photo=photo,
        caption=(
            f"*Хочешь забрать {GIFTS[gift_key]['label']}?* 🎯\n\n"
            f"Всё просто — подпишись на оба канала ниже "
            f"и нажми *«Я подписался!»*\n\n"
            f"⚡️ Проверка проходит мгновенно"
        ),
        parse_mode="Markdown",
        reply_markup=kb_subscribe(),
    )


@dp.callback_query(F.data == "gift_promo")
async def cb_gift_promo(cb: CallbackQuery, state: FSMContext) -> None:
    user_id = cb.from_user.id
    users.add(user_id)
    stats["gift_clicks"]["gift_promo"] += 1

    if user_id in used_gifts:
        await cb.answer(
            f"❌ Ты уже получил: {used_gifts[user_id]}",
            show_alert=True,
        )
        return

    await state.set_state(UserState.enter_promo)
    await cb.answer()
    await safe_delete(cb.message)
    await cb.message.answer_photo(
        photo=PHOTO_PROMO,
        caption=(
            "🎟 *Введи промокод*\n\n"
            "Просто напиши код в этот чат — и всё 🙌\n\n"
            "_Для отмены — /cancel_"
        ),
        parse_mode="Markdown",
        reply_markup=kb_back(),
    )


@dp.callback_query(F.data == "referrals")
async def cb_referrals(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    users.add(user_id)
    invited = invites_count.get(user_id, 0)
    remain  = max(REQUIRED_INVITES - invited, 0)
    link    = make_ref_link(await bot_username(), user_id)
    bar     = progress_bar(invited, REQUIRED_INVITES)

    if invited >= REQUIRED_INVITES:
        status_line = "✅ *Условие выполнено! Можешь получить подарок*"
    else:
        status_line = f"⏳ Осталось пригласить: *{remain}*"

    text = (
        f"👥 *Реферальная система*\n\n"
        f"{bar}\n"
        f"Приглашено: *{invited} из {REQUIRED_INVITES}*\n"
        f"{status_line}\n\n"
        f"🔗 *Твоя ссылка:*\n"
        f"`{link}`\n\n"
        f"_Поделись с друзьями — как только они подпишутся, "
        f"прогресс обновится автоматически_"
    )
    await cb.answer()
    await safe_delete(cb.message)
    await cb.message.answer_photo(
        photo=PHOTO_REFERRALS,
        caption=text,
        parse_mode="Markdown",
        reply_markup=kb_referrals()
    )


@dp.callback_query(F.data == "get_link")
async def cb_get_link(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    users.add(user_id)
    invited = invites_count.get(user_id, 0)
    remain  = max(REQUIRED_INVITES - invited, 0)
    link    = make_ref_link(await bot_username(), user_id)
    bar     = progress_bar(invited, REQUIRED_INVITES)
    await cb.answer()
    await cb.message.answer_photo(
        photo=PHOTO_REFERRALS,
        caption=(
            f"🔗 *Твоя реферальная ссылка:*\n\n"
            f"`{link}`\n\n"
            f"{bar}\n"
            f"Приглашено: *{invited}/{REQUIRED_INVITES}* · Осталось: *{remain}*\n\n"
            f"_Скопируй ссылку и отправь друзьям 👆_"
        ),
        parse_mode="Markdown",
    )


@dp.callback_query(F.data == "check_refs")
async def cb_check_refs(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    users.add(user_id)
    invited = invites_count.get(user_id, 0)
    remain  = max(REQUIRED_INVITES - invited, 0)
    bar     = progress_bar(invited, REQUIRED_INVITES)

    if invited >= REQUIRED_INVITES:
        await cb.answer("✅ Условие выполнено!", show_alert=True)
        await safe_delete(cb.message)
        await cb.message.answer_photo(
            photo=PHOTO_REFERRALS,
            caption=(
                f"🏆 *Отлично! Ты пригласил {invited} друзей!*\n\n"
                f"{bar}\n\n"
                f"Возвращайся в главное меню и забирай подарок 🎁"
            ),
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )
    else:
        link = make_ref_link(await bot_username(), user_id)
        await cb.answer(f"Осталось: {remain}", show_alert=True)
        await cb.message.answer_photo(
            photo=PHOTO_REFERRALS,
            caption=(
                f"🔄 *Прогресс обновлён*\n\n"
                f"{bar}\n"
                f"Приглашено: *{invited}/{REQUIRED_INVITES}* · Осталось: *{remain}*\n\n"
                f"🔗 Твоя ссылка:\n`{link}`"
            ),
            parse_mode="Markdown",
        )

# ╔══════════════════════════════════════════════════╗
# ║              ПРОВЕРКА ПОДПИСКИ                  ║
# ╚══════════════════════════════════════════════════╝

@dp.callback_query(F.data == "check_sub")
async def cb_check_sub(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer("🔍 Проверяю...")
    user_id = cb.from_user.id
    users.add(user_id)
    stats["sub_checks"] += 1

    sub1 = await is_subscribed(user_id, CHANNEL_1_ID)
    sub2 = await is_subscribed(user_id, CHANNEL_2_ID)

    if not (sub1 and sub2):
        missing = []
        if not sub1: missing.append(f"• {CHANNEL_1_NAME}")
        if not sub2: missing.append(f"• {CHANNEL_2_NAME}")
        text = (
            "😔 *Подписка не найдена*\n\n"
            "Ты ещё не подписан на:\n"
            + "\n".join(missing)
            + "\n\nПодпишись на каналы и нажми кнопку снова 👇"
        )
        await safe_delete(cb.message)
        await cb.message.answer(
            text, parse_mode="Markdown", reply_markup=kb_subscribe()
        )
        return

    # Зачесть реферала
    if user_id in pending_refs:
        ref_id = pending_refs.pop(user_id)
        invites_count[ref_id] = invites_count.get(ref_id, 0) + 1
        stats["total_refs"] += 1
        count_now = invites_count[ref_id]
        bar       = progress_bar(count_now, REQUIRED_INVITES)
        remain    = max(REQUIRED_INVITES - count_now, 0)
        try:
            if count_now >= REQUIRED_INVITES:
                ref_msg = (
                    f"🎉 *+1 реферал!*\n\n"
                    f"👤 {cb.from_user.full_name} подписался по твоей ссылке\n\n"
                    f"{bar}\n"
                    f"*{count_now}/{REQUIRED_INVITES}* — условие выполнено! "
                    f"Забирай подарок 🎁"
                )
            else:
                ref_msg = (
                    f"🎉 *+1 реферал!*\n\n"
                    f"👤 {cb.from_user.full_name} подписался по твоей ссылке\n\n"
                    f"{bar}\n"
                    f"*{count_now}/{REQUIRED_INVITES}* — осталось пригласить *{remain}*"
                )
            await bot.send_message(ref_id, ref_msg, parse_mode="Markdown")
        except Exception:
            pass
        await safe_delete(cb.message)
        await cb.message.answer_photo(
            photo=PHOTO_URL,
            caption=(
                "✅ *Спасибо за подписку!*\n\n"
                "Реферал засчитан твоему другу 🤝\n\n"
                "Теперь ты тоже можешь участвовать — "
                "выбери подарок в главном меню 👇"
            ),
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )
        return

    # Проверка рефералов
    invited = invites_count.get(user_id, 0)
    if invited < REQUIRED_INVITES:
        remain = REQUIRED_INVITES - invited
        link   = make_ref_link(await bot_username(), user_id)
        bar    = progress_bar(invited, REQUIRED_INVITES)
        await safe_delete(cb.message)
        await cb.message.answer_photo(
            photo=PHOTO_REFERRALS,
            caption=(
                f"✅ *Подписка есть, но не всё готово!*\n\n"
                f"Нужно ещё пригласить друзей:\n\n"
                f"{bar}\n"
                f"*{invited}/{REQUIRED_INVITES}* — осталось *{remain}*\n\n"
                f"🔗 Твоя ссылка:\n`{link}`\n\n"
                f"_Поделись с друзьями и возвращайся!_"
            ),
            parse_mode="Markdown",
            reply_markup=kb_referrals(),
        )
        return

    # Уже получал?
    if user_id in used_gifts:
        await safe_delete(cb.message)
        await cb.message.answer_photo(
            photo=PHOTO_URL,
            caption=(
                f"🎁 *Ты уже получил свой подарок:* {used_gifts[user_id]}\n\n"
                f"По вопросам пиши: {CONTACT_USERNAME}"
            ),
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )
        return

    # Выдача подарка
    data      = await state.get_data()
    gift_key  = data.get("selected_gift", "gift_30")
    gift_info = GIFTS.get(gift_key, {"name": "подарок", "label": "🎁 Подарок", "emoji": "🎁"})

    used_gifts[user_id] = gift_info["name"]
    stats["gifts_given"] += 1

    # Уведомление — HTML, данные пользователя экранированы
    safe_name = html_escape(cb.from_user.full_name)
    await notify_admins(
        f"🎁 <b>Подарок выдан!</b>\n\n"
        f"👤 <a href='tg://user?id={user_id}'>{safe_name}</a>\n"
        f"📲 {get_username_line(cb.from_user)}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"🎀 {html_escape(gift_info['name'])}\n"
        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    await safe_delete(cb.message)
    await cb.message.answer_photo(
        photo=PHOTO_URL,
        caption=(
            f"🎊 *Поздравляем! Ты выполнил все условия!*\n\n"
            f"Твой подарок: *{gift_info['label']}* {gift_info['emoji']}\n\n"
            f"📬 Напиши нам, чтобы его получить:\n"
            f"➡️ {CONTACT_USERNAME}"
        ),
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )
    await state.clear()

# ╔══════════════════════════════════════════════════╗
# ║                    ПРОМОКОДЫ                    ║
# ╚══════════════════════════════════════════════════╝

@dp.message(UserState.enter_promo)
async def process_promo(msg: Message, state: FSMContext) -> None:
    user_id = msg.from_user.id
    users.add(user_id)
    code    = msg.text.strip().upper()
    stats["promo_tries"] += 1

    if user_id in used_gifts:
        await msg.answer_photo(
            photo=PHOTO_URL,
            caption=(
                f"🎁 *Ты уже получил подарок:* {used_gifts[user_id]}\n\n"
                f"По вопросам: {CONTACT_USERNAME}"
            ),
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )
        await state.clear()
        return

    promo = promocodes.get(code)

    if not promo:
        await msg.answer_photo(
            photo=PHOTO_PROMO,
            caption=(
                "❌ *Промокод не найден*\n\n"
                "Проверь правильность написания и попробуй снова, "
                "или нажми /cancel для отмены"
            ),
            parse_mode="Markdown",
        )
        return

    if datetime.now() > promo["expires"]:
        await msg.answer_photo(
            photo=PHOTO_URL,
            caption=(
                "⏰ *Промокод истёк*\n\n"
                "Срок действия этого кода закончился"
            ),
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )
        await state.clear()
        return

    if promo["remaining"] <= 0:
        await msg.answer_photo(
            photo=PHOTO_URL,
            caption=(
                "😔 *Промокод уже использован*\n\n"
                "Все активации этого кода закончились"
            ),
            parse_mode="Markdown",
            reply_markup=kb_main(),
        )
        await state.clear()
        return

    # Активация
    promo["remaining"] -= 1
    used_gifts[user_id] = promo["name"]
    stats["promo_ok"]    += 1
    stats["gifts_given"] += 1

    # Уведомление — HTML, данные пользователя экранированы
    safe_name = html_escape(msg.from_user.full_name)
    await notify_admins(
        f"🎟 <b>Промокод активирован!</b>\n\n"
        f"👤 <a href='tg://user?id={user_id}'>{safe_name}</a>\n"
        f"📲 {get_username_line(msg.from_user)}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"📝 Код: <code>{html_escape(code)}</code>\n"
        f"🎁 Подарок: {html_escape(promo['name'])}\n"
        f"📊 Осталось активаций: {promo['remaining']}/{promo['activations']}\n"
        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )

    await msg.answer_photo(
        photo=PHOTO_URL,
        caption=(
            f"✅ *Промокод принят!*\n\n"
            f"Твой подарок: *{promo['name']}*\n\n"
            f"📬 Напиши нам для получения:\n"
            f"➡️ {CONTACT_USERNAME}"
        ),
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )
    await state.clear()

# ╔══════════════════════════════════════════════════╗
# ║                  АДМИН-ПАНЕЛЬ                   ║
# ╚══════════════════════════════════════════════════╝

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@dp.callback_query(F.data == "adm_stats")
async def cb_adm_stats(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True)
        return

    gc            = stats["gift_clicks"]
    total_clicks  = sum(gc.values())
    active_promos = sum(
        1 for p in promocodes.values()
        if datetime.now() <= p["expires"] and p["remaining"] > 0
    )
    total_promos = len(promocodes)
    uptime       = format_uptime()

    conv_gifts = (
        f"{stats['gifts_given'] / total_clicks * 100:.1f}%"
        if total_clicks > 0 else "—"
    )
    conv_promo = (
        f"{stats['promo_ok'] / stats['promo_tries'] * 100:.1f}%"
        if stats["promo_tries"] > 0 else "—"
    )

    text = (
        f"📊 *Статистика*\n"
        f"{'─' * 30}\n\n"

        f"👥 *Пользователей:* {len(users)}\n"
        f"📢 *Каналов:* 2\n"
        f"⏱ *Аптайм:* {uptime}\n\n"

        f"{'─' * 30}\n"
        f"🎁 *Подарки*\n\n"

        f"Нажатий на подарки: *{total_clicks}*\n"
        f"   ├ 💰 30 Звёзд — {gc['gift_30']}\n"
        f"   ├ 🧸 3 Мишки — {gc['gift_mice']}\n"
        f"   └ 🎟 Промокод — {gc['gift_promo']}\n\n"

        f"✅ Нажатий «Я подписался»: *{stats['sub_checks']}*\n"
        f"🌹 Подарков выдано: *{stats['gifts_given']}*\n"
        f"📈 Конверсия в подарок: *{conv_gifts}*\n\n"

        f"{'─' * 30}\n"
        f"🎟 *Промокоды*\n\n"

        f"Введено промокодов: *{stats['promo_tries']}*\n"
        f"Успешно активировано: *{stats['promo_ok']}*\n"
        f"Конверсия: *{conv_promo}*\n"
        f"Активных кодов: *{active_promos} из {total_promos}*\n\n"

        f"{'─' * 30}\n"
        f"🔗 *Рефералы*\n\n"

        f"Всего засчитано: *{stats['total_refs']}*\n"
        f"Порог для подарка: *{REQUIRED_INVITES}*"
    )

    await cb.answer()
    await safe_delete(cb.message)
    await cb.message.answer_photo(
        photo=PHOTO_STATS,
        caption=text,
        parse_mode="Markdown",
        reply_markup=kb_admin()
    )


@dp.callback_query(F.data == "adm_list")
async def cb_adm_list(cb: CallbackQuery) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True)
        return
    if not promocodes:
        await cb.answer("Промокодов пока нет", show_alert=True)
        return

    now   = datetime.now()
    lines = ["📋 *Список промокодов*\n"]
    for code, p in promocodes.items():
        is_expired = now > p["expires"]
        is_empty   = p["remaining"] <= 0
        if is_expired:
            status = "⛔️ истёк"
        elif is_empty:
            status = "🚫 исчерпан"
        else:
            status = f"✅ до {p['expires'].strftime('%d.%m.%Y')}"

        used = p["activations"] - p["remaining"]
        bar  = progress_bar(used, p["activations"])
        lines.append(
            f"🔹 `{code}`\n"
            f"   🎁 {p['name']}\n"
            f"   {bar}\n"
            f"   📊 {p['remaining']}/{p['activations']} осталось\n"
            f"   {status}\n"
        )

    await cb.answer()
    await safe_delete(cb.message)
    await cb.message.answer_photo(
        photo=PHOTO_STATS,
        caption="\n".join(lines),
        parse_mode="Markdown",
        reply_markup=kb_admin()
    )


@dp.callback_query(F.data == "adm_create")
async def cb_adm_create(cb: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(cb.from_user.id):
        await cb.answer("❌ Нет доступа", show_alert=True)
        return
    await state.set_state(AdminState.promo_name)
    await cb.answer()
    await cb.message.answer_photo(
        photo=PHOTO_PROMO,
        caption=(
            "✏️ *Создание промокода — шаг 1/3*\n\n"
            "Введи название подарка:\n"
            "_Например: «30 Звёзд» или «3 Мишки»_\n\n"
            "/cancel — отмена"
        ),
        parse_mode="Markdown",
    )


@dp.message(AdminState.promo_name)
async def adm_promo_name(msg: Message, state: FSMContext) -> None:
    await state.update_data(promo_name=msg.text.strip())
    await state.set_state(AdminState.promo_activations)
    await msg.answer_photo(
        photo=PHOTO_PROMO,
        caption=(
            "🔢 *Шаг 2/3 — Количество активаций*\n\n"
            "Сколько раз можно использовать этот промокод?\n\n"
            "/cancel — отмена"
        ),
        parse_mode="Markdown",
    )


@dp.message(AdminState.promo_activations)
async def adm_promo_activations(msg: Message, state: FSMContext) -> None:
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await msg.answer("❌ Введи целое число больше 0")
        return
    await state.update_data(promo_activations=count)
    await state.set_state(AdminState.promo_days)
    await msg.answer_photo(
        photo=PHOTO_PROMO,
        caption=(
            "📅 *Шаг 3/3 — Срок действия*\n\n"
            "На сколько дней создать промокод?\n\n"
            "/cancel — отмена"
        ),
        parse_mode="Markdown",
    )


@dp.message(AdminState.promo_days)
async def adm_promo_days(msg: Message, state: FSMContext) -> None:
    try:
        days = int(msg.text.strip())
        if days < 1:
            raise ValueError
    except ValueError:
        await msg.answer("❌ Введи целое число больше 0")
        return

    data    = await state.get_data()
    name    = data["promo_name"]
    acts    = data["promo_activations"]
    code    = gen_promo_code()
    expires = datetime.now() + timedelta(days=days)

    promocodes[code] = {
        "name":        name,
        "activations": acts,
        "remaining":   acts,
        "expires":     expires,
        "created_by":  msg.from_user.id,
        "created_at":  datetime.now(),
    }

    await state.clear()
    await msg.answer_photo(
        photo=PHOTO_URL,
        caption=(
            f"✅ *Промокод создан!*\n\n"
            f"📌 Код: `{code}`\n"
            f"🎁 Подарок: *{name}*\n"
            f"🔢 Активаций: *{acts}*\n"
            f"📅 Действует до: *{expires.strftime('%d.%m.%Y %H:%M')}*\n\n"
            f"_Скопируй код и отправь пользователям 👆_"
        ),
        parse_mode="Markdown",
        reply_markup=kb_admin(),
    )

# ╔══════════════════════════════════════════════════╗
# ║               ВЕБ-СЕРВЕР (RENDER)               ║
# ╚══════════════════════════════════════════════════╝

async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="OK")


async def start_webserver() -> None:
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    log.info("Веб-сервер запущен на порту 10000")

# ╔══════════════════════════════════════════════════╗
# ║                     ЗАПУСК                      ║
# ╚══════════════════════════════════════════════════╝

async def main() -> None:
    log.info("=" * 52)
    log.info("  NECROCIDE / HESITEY BOT — СТАРТ")
    log.info(f"  Админы:    {ADMIN_IDS}")
    log.info(f"  Рефералов: {REQUIRED_INVITES}")
    log.info("=" * 52)
    await start_webserver()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
