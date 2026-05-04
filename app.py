import asyncio
import random
import string
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = os.environ["BOT_TOKEN"]

CHANNEL_1_ID = -1003993803454
CHANNEL_2_ID = -1003859905398

ADMIN_IDS = [8377328708, 995258854]

REQUIRED_INVITES = 7
RANDOM_CHANCE = 5

PHOTO_URL = "https://i.postimg.cc/90Ryk33F/file-000000005fd87243ba6d7497f8878878.png"

# Словари для хранения данных
invites_count = {}
pending_referrals = {}
promocodes = {}
used_promocodes = {}
used_gifts = {}  # ОСНОВНОЙ ЗАЩИТА - здесь хранятся все полученные подарки

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========== СОСТОЯНИЯ FSM ==========
class AdminStates(StatesGroup):
    waiting_for_promocode_name = State()
    waiting_for_activations_count = State()
    waiting_for_expiry_days = State()

class UserStates(StatesGroup):
    waiting_for_promocode_input = State()

# ========== КЛАВИАТУРЫ ==========
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 30 ЗВЁЗД", callback_data="gift_30")],
        [InlineKeyboardButton(text="🧸 3 МИШКИ", callback_data="gift_mice")],
        [InlineKeyboardButton(text="🎟 ПРОМОКОД", callback_data="gift_promo")],
        [InlineKeyboardButton(text="👥 РЕФЕРАЛЫ", callback_data="referrals")]
    ])
    return keyboard

def admin_panel_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 СОЗДАТЬ ПРОМОКОД", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="📋 СПИСОК ПРОМОКОДОВ", callback_data="admin_list_promo")],
        [InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="admin_stats")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_menu")]
    ])
    return keyboard

def subscribe_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 NECROCIDE", url="https://t.me/+_W1Hit0AXMExMzVi")],
        [InlineKeyboardButton(text="📢 ПЕРЕХОДНИК HESITEY", url="https://t.me/KultovHesitey")],
        [InlineKeyboardButton(text="✅ Я ПОДПИСАЛСЯ", callback_data="check_subscribe")]
    ])
    return keyboard

def invites_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 ПОЛУЧИТЬ ССЫЛКУ", callback_data="get_invite_link")],
        [InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ СТАТУС", callback_data="check_invites")],
        [InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_menu")]
    ])
    return keyboard

# ========== ФУНКЦИИ ==========
async def check_subscription(user_id: int, channel_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

def generate_invite_link(user_id: int) -> str:
    return f"https://t.me/{(bot.me.username)}?start={user_id}"

def generate_promocode() -> str:
    letters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters) for _ in range(10))

async def send_main_menu(message_or_callback):
    if isinstance(message_or_callback, types.CallbackQuery):
        msg = message_or_callback.message
        await msg.delete()
        await msg.answer_photo(
            photo=PHOTO_URL,
            caption="🌟 *ДОБРО ПОЖАЛОВАТЬ В БОТА!* 🌟\n\n👇 *ВЫБЕРИ ДЕЙСТВИЕ:* 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    else:
        await message_or_callback.answer_photo(
            photo=PHOTO_URL,
            caption="🌟 *ДОБРО ПОЖАЛОВАТЬ В БОТА!* 🌟\n\n👇 *ВЫБЕРИ ДЕЙСТВИЕ:* 👇",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

# ========== КОМАНДА /START ==========
@dp.message(Command("start"))
async def start_command(message: types.Message):
    args = message.text.split()
    user_id = message.from_user.id
    
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id:
            if user_id not in pending_referrals:
                pending_referrals[user_id] = referrer_id
                await message.answer(
                    "🔗 *ВЫ БЫЛИ ПРИГЛАШЕНЫ!* 🔗\n\n"
                    "📌 *Чтобы реферал засчитался:*\n"
                    "1️⃣ ПОДПИШИСЬ НА КАНАЛЫ\n"
                    "2️⃣ НАЖМИ «Я ПОДПИСАЛСЯ»\n\n"
                    "✨ После этого твой друг получит +1 к приглашениям! ✨",
                    parse_mode="Markdown"
                )
    
    await send_main_menu(message)

# ========== КОМАНДА /ADMIN ==========
@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ *НЕТ ДОСТУПА!* ❌", parse_mode="Markdown")
        return
    
    await message.answer(
        "🛡 *АДМИН-ПАНЕЛЬ* 🛡\n\n👇 *ВЫБЕРИ ДЕЙСТВИЕ:* 👇",
        parse_mode="Markdown",
        reply_markup=admin_panel_keyboard()
    )

# ========== ОБРАБОТКА ГЛАВНОГО МЕНЮ ==========
@dp.callback_query(lambda c: c.data in ["gift_30", "gift_mice", "gift_promo", "referrals", "back_to_menu", "admin_stats", "admin_create_promo", "admin_list_promo"])
async def handle_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # НАЗАД В МЕНЮ
    if callback.data == "back_to_menu":
        await send_main_menu(callback)
        await callback.answer()
        return
    
    # АДМИН СТАТИСТИКА
    if callback.data == "admin_stats":
        if user_id not in ADMIN_IDS:
            await callback.answer("Нет доступа!", show_alert=True)
            return
        total_invites = sum(invites_count.values())
        active_promos = len(promocodes)
        pending = len(pending_referrals)
        text = (f"📊 *СТАТИСТИКА БОТА* 📊\n\n"
                f"👥 Всего приглашений: {total_invites}\n"
                f"⏳ Ожидают: {pending}\n"
                f"🎟 Промокодов: {active_promos}\n"
                f"👤 Пользователей: {len(invites_count)}\n"
                f"🎯 Нужно: {REQUIRED_INVITES}")
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        await callback.answer()
        return
    
    # АДМИН СПИСОК ПРОМОКОДОВ
    if callback.data == "admin_list_promo":
        if user_id not in ADMIN_IDS:
            await callback.answer("Нет доступа!", show_alert=True)
            return
        if not promocodes:
            await callback.message.delete()
            await callback.message.answer("📭 *НЕТ АКТИВНЫХ ПРОМОКОДОВ*", parse_mode="Markdown", reply_markup=admin_panel_keyboard())
            await callback.answer()
            return
        text = "*📋 СПИСОК ПРОМОКОДОВ:*\n\n"
        for code, data in promocodes.items():
            text += (f"🔹 `{code}`\n"
                     f"   🎁 {data['name']}\n"
                     f"   📊 {data['remaining']}/{data['activations']}\n"
                     f"   📅 {data['expires'].strftime('%d.%m.%Y')}\n\n")
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=admin_panel_keyboard())
        await callback.answer()
        return
    
    # АДМИН СОЗДАНИЕ ПРОМОКОДА
    if callback.data == "admin_create_promo":
        if user_id not in ADMIN_IDS:
            await callback.answer("Нет доступа!", show_alert=True)
            return
        await callback.message.answer("✏️ *ВВЕДИ НАЗВАНИЕ ПРОМОКОДА:*", parse_mode="Markdown")
        await state.set_state(AdminStates.waiting_for_promocode_name)
        await callback.answer()
        return
    
    # РЕФЕРАЛЫ
    if callback.data == "referrals":
        invited = invites_count.get(user_id, 0)
        remaining = REQUIRED_INVITES - invited
        link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
        text = (f"👥 *РЕФЕРАЛЬНАЯ СИСТЕМА* 👥\n\n"
                f"📎 *ССЫЛКА:* `{link}`\n"
                f"👤 *ПРИГЛАШЕНО:* {invited}/{REQUIRED_INVITES}\n"
                f"📌 *ОСТАЛОСЬ:* {remaining}\n\n"
                f"💡 *РЕФЕРАЛ ЗАСЧИТАЕТСЯ ТОЛЬКО ПОСЛЕ ПОДПИСКИ ДРУГА!*")
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=invites_keyboard())
        await callback.answer()
        return
    
    # ПРОМОКОД - ПРОВЕРКА ЗАЩИТЫ
    if callback.data == "gift_promo":
        if user_id in used_gifts:
            await callback.answer("❌ ТЫ УЖЕ ПОЛУЧИЛ ПОДАРОК! ❌", show_alert=True)
            return
        await state.set_state(UserStates.waiting_for_promocode_input)
        await callback.message.delete()
        await callback.message.answer("🎟 *ВВЕДИ ПРОМОКОД:* 🎟\n\nПросто напиши код в чат", parse_mode="Markdown")
        await callback.answer()
        return
    
    # ПОДАРКИ (30 ЗВЕЗД ИЛИ 3 МИШКИ) - ПРОВЕРКА ЗАЩИТЫ
    if user_id in used_gifts:
        await callback.answer("❌ ТЫ УЖЕ ПОЛУЧИЛ ПОДАРОК! ОДИН ПОЛЬЗОВАТЕЛЬ - ОДИН ПОДАРОК! ❌", show_alert=True)
        return
    
    await state.update_data(selected_gift=callback.data)
    await callback.message.delete()
    await callback.message.answer(
        "📢 *ЧТОБЫ ПОЛУЧИТЬ ПОДАРОК, ПОДПИШИСЬ НА КАНАЛЫ И НАЖМИ КНОПКУ:*",
        parse_mode="Markdown",
        reply_markup=subscribe_keyboard()
    )
    await callback.answer()

# ========== РЕФЕРАЛЬНЫЕ КНОПКИ ==========
@dp.callback_query(lambda c: c.data in ["get_invite_link", "check_invites"])
async def handle_referrals(callback: CallbackQuery):
    user_id = callback.from_user.id
    invited = invites_count.get(user_id, 0)
    
    if callback.data == "get_invite_link":
        link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
        remaining = REQUIRED_INVITES - invited
        await callback.message.answer(
            f"🔗 *ТВОЯ РЕФЕРАЛЬНАЯ ССЫЛКА:* 🔗\n\n`{link}`\n\n"
            f"👥 *ПРИГЛАШЕНО:* {invited}/{REQUIRED_INVITES}\n"
            f"📌 *ОСТАЛОСЬ:* {remaining}",
            parse_mode="Markdown"
        )
        await callback.answer()
    elif callback.data == "check_invites":
        if invited >= REQUIRED_INVITES:
            await callback.message.delete()
            await callback.message.answer(
                f"✅ *ОТЛИЧНО! ТЫ ПРИГЛАСИЛ {invited} ДРУЗЕЙ!* ✅\n\n"
                f"🎁 *ТЕПЕРЬ ВЫБЕРИ ПОДАРОК В ГЛАВНОМ МЕНЮ!*",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            remaining = REQUIRED_INVITES - invited
            await callback.message.answer(
                f"👥 *У ТЕБЯ {invited}/{REQUIRED_INVITES} ПРИГЛАШЕННЫХ*\n\n📌 *ОСТАЛОСЬ:* {remaining}",
                parse_mode="Markdown"
            )
        await callback.answer()

# ========== ПРОВЕРКА ПОДПИСКИ (САМЫЙ ВАЖНЫЙ ХЕНДЛЕР) ==========
@dp.callback_query(lambda c: c.data == "check_subscribe")
async def handle_check_subscribe(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🔍 ПРОВЕРЯЮ ПОДПИСКУ...", show_alert=False)
    
    user_id = callback.from_user.id
    is_subscribed_1 = await check_subscription(user_id, CHANNEL_1_ID)
    is_subscribed_2 = await check_subscription(user_id, CHANNEL_2_ID)
    
    if is_subscribed_1 and is_subscribed_2:
        # ===== ЗАЧИСЛЕНИЕ РЕФЕРАЛКИ =====
        if user_id in pending_referrals:
            referrer_id = pending_referrals[user_id]
            if referrer_id not in invites_count:
                invites_count[referrer_id] = 0
            invites_count[referrer_id] += 1
            del pending_referrals[user_id]
            try:
                await bot.send_message(
                    referrer_id,
                    f"✅ *НОВОЕ ПРИГЛАШЕНИЕ!* ✅\n\n👤 *ДРУГ:* {callback.from_user.full_name}\n📊 *ТЕПЕРЬ У ТЕБЯ:* {invites_count[referrer_id]}/{REQUIRED_INVITES}",
                    parse_mode="Markdown"
                )
            except:
                pass
            await callback.message.delete()
            await callback.message.answer(
                "✅ *СПАСИБО ЗА ПОДПИСКУ!* ✅\n\n🎁 *РЕФЕРАЛ ЗАСЧИТАН ТВОЕМУ ДРУГУ!*\n\n📌 *ТЕПЕРЬ ВЫБЕРИ ПОДАРОК В ГЛАВНОМ МЕНЮ!*",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
            await callback.answer()
            return
        
        # ===== ОСНОВНАЯ ЗАЩИТА - ПРОВЕРКА НЕ ПОЛУЧИЛ ЛИ УЖЕ ПОДАРОК =====
        if user_id in used_gifts:
            await callback.message.delete()
            await callback.message.answer(
                f"❌ *ТЫ УЖЕ ПОЛУЧИЛ ПОДАРОК:* {used_gifts[user_id]} ❌\n\n📌 *ОДИН ПОЛЬЗОВАТЕЛЬ - ОДИН ПОДАРОК!*",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
            await callback.answer()
            return
        
        user_data = await state.get_data()
        selected_gift = user_data.get("selected_gift", "подарок")
        gift_name = "30 ЗВЕЗД" if selected_gift == "gift_30" else "3 МИШКИ" if selected_gift == "gift_mice" else "подарок"
        
        chance = random.randint(1, 100)
        
        if chance <= RANDOM_CHANCE:
            used_gifts[user_id] = gift_name
            await callback.message.delete()
            await callback.message.answer(
                f"🎁 *ХОЧЕШЬ И ВПРАВДУ ПОДАРОК?* 🎁\n\n"
                f"ОТПРАВЬ 5 ЛЮДЯМ ЭТОГО БОТА СО СЛОВАМИ:\n"
                f"*«ПЕРЕЙДИТЕ В БОТА И ПОДПИШИТЕСЬ НА КАНАЛЫ»* - @NecrocideBot\n\n"
                f"⚡ *КАК ТОЛЬКО СДЕЛАЕШЬ - НАПИШИ МНЕ В ЛС @FuckHesitey*\n\n"
                f"🎁 *И ПОЛУЧИ ПОДАРОК БЕЗ ШУТОК!*\n\n✨ *ТВОЙ ПОДАРОК:* {gift_name} ✨",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        else:
            invited = invites_count.get(user_id, 0)
            if invited >= REQUIRED_INVITES:
                used_gifts[user_id] = gift_name
                await callback.message.delete()
                await callback.message.answer(
                    f"✅ *ТЫ ПОДПИСАЛСЯ НА КАНАЛЫ!* ✅\n\n🎁 *ЗА ПОДАРКОМ ОБРАЩАЙСЯ:* @FuckHesitey",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
            else:
                remaining = REQUIRED_INVITES - invited
                await callback.message.delete()
                await callback.message.answer(
                    f"✅ *ТЫ ПОДПИСАЛСЯ НА КАНАЛЫ!* ✅\n\n"
                    f"🎁 *ЗА ПОДАРКОМ ОБРАЩАЙСЯ:* @FuckHesitey\n\n"
                    f"👥 *ПРИГЛАСИ ЕЩЕ {remaining} ДРУЗЕЙ, ЧТОБЫ ПОЛУЧИТЬ ГАРАНТИРОВАННЫЙ ПОДАРОК!*",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard()
                )
    else:
        not_subscribed = []
        if not is_subscribed_1:
            not_subscribed.append("📢 NECROCIDE")
        if not is_subscribed_2:
            not_subscribed.append("📢 ПЕРЕХОДНИК HESITEY")
        text = ("❌ *ТЫ НЕ ПОДПИСАН НА КАНАЛЫ:* ❌\n\n" + "\n".join(not_subscribed) + "\n\n📌 *ПОДПИШИСЬ И НАЖМИ СНОВА!*")
        await callback.message.delete()
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=subscribe_keyboard())

# ========== ОБРАБОТКА ВВОДА ПРОМОКОДА ==========
@dp.message(UserStates.waiting_for_promocode_input)
async def process_promocode(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.strip().upper()
    
    # ОСНОВНАЯ ЗАЩИТА - ПРОВЕРКА НЕ ПОЛУЧИЛ ЛИ УЖЕ ПОДАРОК
    if user_id in used_gifts:
        await message.answer(
            f"❌ *ТЫ УЖЕ ПОЛУЧИЛ ПОДАРОК:* {used_gifts[user_id]} ❌\n\n📌 *ОДИН ПОЛЬЗОВАТЕЛЬ - ОДИН ПОДАРОК!*",
            parse_mode="Markdown"
        )
        await state.clear()
        return
    
    if code not in promocodes:
        await message.answer("❌ *НЕВЕРНЫЙ ПРОМОКОД!* ❌\n\nПопробуй ещё раз.", parse_mode="Markdown")
        await state.clear()
        return
    
    promo = promocodes[code]
    
    if datetime.now() > promo["expires"]:
        await message.answer("❌ *ПРОМОКОД ПРОСРОЧЕН!* ❌", parse_mode="Markdown")
        await state.clear()
        return
    
    if promo["remaining"] <= 0:
        await message.answer("❌ *ПРОМОКОД УЖЕ ИСПОЛЬЗОВАН!* ❌", parse_mode="Markdown")
        await state.clear()
        return
    
    # АКТИВАЦИЯ ПРОМОКОДА
    promocodes[code]["remaining"] -= 1
    used_promocodes[user_id] = code
    used_gifts[user_id] = promo["name"]
    
    await message.answer(
        f"✅ *ПРОМОКОД АКТИВИРОВАН!* ✅\n\n🏷 *ТЫ ПОЛУЧИЛ:* {promo['name']}\n\n🎁 *ПО ВСЕМ ВОПРОСАМ:* @FuckHesitey",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()

# ========== СОЗДАНИЕ ПРОМОКОДА (АДМИН) ==========
@dp.message(AdminStates.waiting_for_promocode_name)
async def get_promo_name(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ ОТМЕНЕНО.")
        return
    await state.update_data(promo_name=message.text)
    await message.answer("🔢 *ВВЕДИ КОЛИЧЕСТВО АКТИВАЦИЙ:*", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_activations_count)

@dp.message(AdminStates.waiting_for_activations_count)
async def get_activations(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ ОТМЕНЕНО.")
        return
    try:
        count = int(message.text)
        await state.update_data(activations_count=count)
        await message.answer("📅 *ВВЕДИ СРОК В ДНЯХ:*", parse_mode="Markdown")
        await state.set_state(AdminStates.waiting_for_expiry_days)
    except ValueError:
        await message.answer("❌ ВВЕДИ ЧИСЛО!")

@dp.message(AdminStates.waiting_for_expiry_days)
async def get_days(message: types.Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ ОТМЕНЕНО.")
        return
    try:
        days = int(message.text)
        data = await state.get_data()
        promo_name = data["promo_name"]
        activations = data["activations_count"]
        code = generate_promocode()
        expires = datetime.now() + timedelta(days=days)
        promocodes[code] = {
            "name": promo_name,
            "activations": activations,
            "remaining": activations,
            "expires": expires,
            "created_by": message.from_user.id,
            "created_at": datetime.now()
        }
        await message.answer(
            f"✅ *ПРОМОКОД СОЗДАН!* ✅\n\n📌 *КОД:* `{code}`\n🏷 *ПОДАРОК:* {promo_name}\n🔢 *АКТИВАЦИЙ:* {activations}\n📅 *ДО:* {expires.strftime('%d.%m.%Y %H:%M')}",
            parse_mode="Markdown",
            reply_markup=admin_panel_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ ВВЕДИ ЧИСЛО!")

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_web():
    app_web = web.Application()
    app_web.router.add_get('/', health_check)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("Веб-сервер запущен на порту 10000")
    while True:
        await asyncio.sleep(3600)

# ========== ЗАПУСК ==========
async def main():
    print("=" * 50)
    print("🚀 БОТ ЗАПУЩЕН")
    print("=" * 50)
    print(f"АДМИНЫ: {ADMIN_IDS}")
    print(f"НУЖНО ПРИГЛАСИТЬ: {REQUIRED_INVITES}")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(start_web())
    loop.run_until_complete(main())
