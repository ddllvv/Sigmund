import os
import random
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from telegram import Update, User
from telegram.ext import Application, CommandHandler, ContextTypes, RetryAfter

# Настройка логгирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

DIAGNOSIS_DATA = { ... }  # Оставьте ваши данные без изменений

class MembersCache:
    """Класс для кеширования участников чата"""
    def __init__(self):
        self._cache = {}
    
    def get(self, chat_id: int) -> Optional[List[User]]:
        entry = self._cache.get(chat_id)
        if entry and datetime.now() - entry['time'] < timedelta(minutes=30):
            return entry['members']
        return None
    
    def set(self, chat_id: int, members: List[User]):
        self._cache[chat_id] = {
            'time': datetime.now(),
            'members': members
        }

members_cache = MembersCache()

async def get_chat_members(bot, chat_id: int) -> Optional[List[User]]:
    """Улучшенный метод получения участников чата"""
    try:
        # Пытаемся получить из кеша
        if cached := members_cache.get(chat_id):
            return cached
        
        members = []
        
        # Метод 1: Итерация через get_chat_members (требует прав админа)
        try:
            async for member in bot.get_chat_members(chat_id):
                if not member.user.is_bot:
                    members.append(member.user)
            if members:
                members_cache.set(chat_id, members)
                return members
        except Exception as e:
            logger.warning(f"Method 1 failed: {e}")

        # Метод 2: Получение администраторов (меньше прав)
        try:
            admins = await bot.get_chat_administrators(chat_id)
            members = [a.user for a in admins if not a.user.is_bot]
            if members:
                members_cache.set(chat_id, members)
                return members
        except Exception as e:
            logger.warning(f"Method 2 failed: {e}")

        # Метод 3: Использование информации о сообщении
        return None

    except RetryAfter as e:
        logger.warning(f"RetryAfter: {e}")
        await asyncio.sleep(e.retry_after)
        return await get_chat_members(bot, chat_id)
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

async def diagnose_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный обработчик команд с гарантированным выбором пользователя"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        args = context.args or []
        
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("🚫 Эта команда работает только в группах!")
            return

        # Парсинг аргументов
        level, target = 2, None
        for arg in args:
            if arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)
            elif arg.startswith('@'):
                target = arg[1:].lower()
        
        # Получение участников
        members = await get_chat_members(context.bot, chat.id)
        
        # Стратегии выбора пользователя
        selected_user = None
        
        # Стратегия 1: По упоминанию
        if target:
            selected_user = next((u for u in members if u.username and u.username.lower() == target), None)
        
        # Стратегия 2: Ответ на сообщение
        if not selected_user and update.message.reply_to_message:
            selected_user = update.message.reply_to_message.from_user
        
        # Стратегия 3: Случайный выбор из участников
        if not selected_user and members:
            selected_user = random.choice(members)
        
        # Стратегия 4: Отправитель команды
        if not selected_user:
            selected_user = user
        
        # Форматирование имени
        username = selected_user.username 
        name = f"@{username}" if username else selected_user.full_name
        
        # Генерация диагноза
        data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        await update.message.reply_text(
            f"🔍 Диагноз для {name} (уровень {level}):\n"
            f"{diagnosis}!"
        )

    except RetryAfter as e:
        await update.message.reply_text(f"⚠️ Слишком много запросов. Попробуйте через {e.retry_after} сек.")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка при обработке команды")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация команд
    handlers = [
        CommandHandler("start", start),
        CommandHandler(["diagnose", "dg"], diagnose_command)
    ]
    
    application.add_handlers(handlers)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    if not TOKEN:
        logger.error("❌ Требуется переменная окружения BOT_TOKEN!")
        exit(1)
    main()
