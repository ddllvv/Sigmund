import os
import random
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.error import RetryAfter
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логгирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

DIAGNOSIS_DATA = {
    1: {
        "problems": ["Покраснение", "Зуд", "Икота"],
        "parts": ["уха", "носа", "пальца"],
        "severity": ["начальной стадии"]
    },
    2: {
        "problems": ["Паралич", "Гастрит", "Аритмия"],
        "parts": ["ребра", "колена", "селезёнки"],
        "severity": ["средней тяжести"]
    },
    3: {
        "problems": ["Гангрена", "Дегенерация", "Тромбоз"],
        "parts": ["гипоталамуса", "надкостницы", "яичка"],
        "severity": ["терминальной стадии"]
    }
}

class MembersCache:
    """Кеширование участников чата"""
    def __init__(self):
        self.cache = {}
    
    def get(self, chat_id: int):
        entry = self.cache.get(chat_id)
        if entry and datetime.now() - entry['time'] < timedelta(minutes=30):
            return entry['members']
        return None
    
    def set(self, chat_id: int, members):
        self.cache[chat_id] = {
            'time': datetime.now(),
            'members': members
        }

members_cache = MembersCache()

async def get_chat_members(bot, chat_id: int):
    """Получение участников чата с обработкой ошибок"""
    try:
        if cached := members_cache.get(chat_id):
            return cached
        
        members = []
        async for member in bot.get_chat_members(chat_id):
            if not member.user.is_bot:
                members.append(member.user)
        
        if members:
            members_cache.set(chat_id, members)
        
        return members
    
    except RetryAfter as e:
        logger.warning(f"RetryAfter error: {e}")
        await asyncio.sleep(e.retry_after)
        return await get_chat_members(bot, chat_id)
    
    except Exception as e:
        logger.error(f"Ошибка получения участников: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    await update.message.reply_text(
        "👨⚕️ Бот-диагност\n\n"
        "Команды:\n"
        "/diagnose или /dg [@юзер] [уровень 1-3]\n\n"
        "Примеры:\n"
        "/dg @user 3 - диагноз для @user\n"
        "/diagnose 2 - случайный участник"
    )

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основная логика бота"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        args = context.args or []
        
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("🚫 Только в группах!")
            return

        # Парсинг аргументов
        level = 2
        target_username = None
        
        for arg in args:
            if arg.startswith('@'):
                target_username = arg  # Сохраняем оригинал (@Username)
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Определение цели
        if target_username:
            display_name = target_username
        else:
            members = await get_chat_members(context.bot, chat.id) or []
            if members:
                selected = random.choice(members)
                display_name = f"@{selected.username}" if selected.username else selected.full_name
            else:
                display_name = f"@{user.username}" if user.username else user.full_name

        # Генерация диагноза
        data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        await update.message.reply_text(
            f"🔍 Диагноз для {display_name} (уровень {level}):\n"
            f"{diagnosis}!"
        )

    except RetryAfter as e:
        await update.message.reply_text(f"⏳ Слишком быстро! Ждите {e.retry_after} сек.")
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("❌ Ошибка выполнения")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler(["diagnose", "dg"], diagnose))
    application.run_polling()

if __name__ == "__main__":
    if not TOKEN:
        logger.error("❌ Укажите BOT_TOKEN в переменных окружения!")
        exit(1)
    main()
