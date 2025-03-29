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
    """Кеш участников чата"""
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
        logger.error(f"Error getting members: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "👨⚕️ Бот-диагност для групп\n\n"
        "Используйте команды:\n"
        "/diagnose или /dg [@юзер] [уровень 1-3]\n"
        "Примеры:\n"
        "/dg 2 - случайному участнику\n"
        "/diagnose @username 3"
    )

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик диагностики"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("🚫 Работает только в группах!")
            return

        args = context.args or []
        level = 2
        target_username = None

        # Парсинг аргументов
        for arg in args:
            if arg.startswith('@'):
                target_username = arg[1:].lower()
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Получение участников
        members = await get_chat_members(context.bot, chat.id)
        
        # Поиск пользователя
        selected_user = None
        if target_username:
            selected_user = next(
                (u for u in members if u.username and u.username.lower() == target_username),
                None
            )
        
        if not selected_user and members:
            selected_user = random.choice(members)
        
        if not selected_user:
            selected_user = user

        # Формирование диагноза
        username = selected_user.username or selected_user.full_name
        data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        await update.message.reply_text(
            f"🔍 Диагноз для @{username} (уровень {level}):\n"
            f"{diagnosis}!"
        )

    except RetryAfter as e:
        await update.message.reply_text(f"⚠️ Слишком много запросов. Попробуйте через {e.retry_after} сек.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка при обработке команды")

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler(["diagnose", "dg"], diagnose))
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    if not TOKEN:
        logger.error("❌ Требуется переменная окружения BOT_TOKEN!")
        exit(1)
    main()
