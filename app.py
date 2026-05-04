import asyncio
import random
import string
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, FSInputFile
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========== КОНФІГУРАЦІЯ (НАЛАШТУВАННЯ) ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # токен беремо з Render

CHANNEL_1_ID = -1003993803454   # Necrocide
CHANNEL_2_ID = -1003859905398   # KultovHesitey

ADMIN_IDS = [8377328708, 995258854]   # хто має доступ до /admin

REQUIRED_INVITES = 7     # скільки друзів треба для гарантії
RANDOM_CHANCE = 5         # 5% – шанс отримати особливе повідомлення

PHOTO_URL = "https://i.postimg.cc/90Ryk33F/file-000000005fd87243ba6d7497f8878878.png"

# словники для зберігання даних (в пам'яті)
invites_count = {}         # {user_id: count}
pending_referrals = {}     # {user_id: referrer_id}
promocodes = {}            # {code: {"name": str, "remaining": int, "expires": datetime}}
used_promocodes = {}       # {user_id: code}
used_gifts = {}            # {user_id: gift_name} — ОСНОВНИЙ ЗАХИСТ

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# стани для FSM (машини станів)
class AdminStates(StatesGroup):
    wait_name = State()
    wait_activations = State()
    wait_days = State()

class UserStates(StatesGroup):
    wait_promo = State()

# ========== КЛАВІАТУРИ (КНОПКИ) – КОЛЬОРОВІ, КРАСИВІ ==========
def main_menu_keyboard():
    """Головне меню – кольорові кнопки"""
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 30 ЗІРОК   ✨", callback_data="gift_30")
    builder.button(text="🧸 3 МИШКИ   🐻", callback_data="gift_mice")
    builder.button(text="🎟 ПРОМОКОД   🔥", callback_data="gift_promo")
    builder.button(text="👥 РЕФЕРАЛИ   👥", callback_data="referrals")
    builder.adjust(1)  # по одній кнопці в рядок
    return builder.as_markup()

def subscribe_keyboard():
    """Кнопки підписки на канали"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Necrocide", url="https://t.me/+_W1Hit0AXMExMzVi")
    builder.button(text="📢 Переходник Hesitey", url="https://t.me/KultovHesitey")
    builder.button(text="✅ Я ПІДПИСАВСЯ", callback_data="check_subscribe")
    builder.adjust(1)
    return builder.as_markup()

def admin_panel_keyboard():
    """Адмін-панель (тільки для ADMIN_IDS)"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🆕 СТВОРИТИ ПРО
