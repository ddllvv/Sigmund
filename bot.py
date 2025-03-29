import os
import random
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ChatMemberHandler,
    ChatJoinRequestHandler
)

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

class ChatData:
    """Класс для хранения данных о чате"""
    def __init__(self):
        self.members = {}
        self.last_updated = {}

    async def update_members(self, chat_id: int, bot):
        """Основной метод обновления участников"""
        try:
            members = []
            async for member in bot.get_chat_members(chat_id):
                if not member.user.is_bot:
                    members.append(member.user)
            self.members[chat_id] = members
            self.last_updated[chat_id] = datetime.now()
            logger.info(f"Обновлен список участников для чата {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка обновления участников: {str(e)}")
            await self._fallback_update(chat_id, bot)

    async def _fallback_update(self, chat_id: int, bot):
        """Резервный метод через историю сообщений"""
        try:
            members = []
            async for message in bot.get_chat_history(chat_id, limit=200):
                user = message.from_user
                if user and not user.is_bot and user not in members:
                    members.append(user)
            self.members[chat_id] = members
            logger.warning(f"Использован резервный метод для чата {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка резервного метода: {str(e)}")

    def get_random_member(self, chat_id: int):
        """Получение случайного участника"""
        members = self.members.get(chat_id, [])
        return random.choice(members) if members else None

    def needs_update(self, chat_id: int):
        """Проверка необходимости обновления"""
        last_update = self.last_updated.get(chat_id)
        return not last_update or (datetime.now() - last_update) > timedelta(minutes=30)

chat_data = ChatData()

async def handle_chat_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик событий чата"""
    chat_id = update.effective_chat.id
    if chat_data.needs_update(chat_id):
        await chat_data.update_members(chat_id, context.bot)

async def check_admin(bot, chat_id: int) -> bool:
    """Проверка прав администратора"""
    try:
        admins = await bot.get_chat_administrators(chat_id)
        return any(admin.user.id == bot.id for admin in admins)
    except Exception as e:
        logger.error(f"Ошибка проверки прав: {str(e)}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_id = update.effective_chat.id
    is_admin = await check_admin(context.bot, chat_id)
    
    text = (
        "👨⚕️ Бот-диагност\n\n"
        "Команды:\n"
        "/dg [@юзер] [уровень] - диагноз пользователю\n"
        "/random_dg [уровень] - случайному участнику\n"
        "\nСтатус: "
        f"{'✅ Бот администратор' if is_admin else '⚠️ Требуются права администратора!'}"
    )
    await update.message.reply_text(text)
    await chat_data.update_members(chat_id, context.bot)

async def random_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /random_dg"""
    try:
        chat = update.effective_chat
        args = context.args or []
        
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("🚫 Только в группах!")
            return

        # Обновляем список участников при необходимости
        if chat_data.needs_update(chat.id):
            await chat_data.update_members(chat.id, context.bot)

        # Получаем участников
        members = chat_data.members.get(chat.id, [])
        if not members:
            await update.message.reply_text("😢 Не удалось получить участников")
            return

        # Парсинг уровня
        level = 2
        for arg in args:
            if arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Выбор участника
        user = random.choice(members)
        username = f"@{user.username}" if user.username else user.full_name

        # Генерация диагноза
        data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        await update.message.reply_text(
            f"🎲 Случайный диагноз для {username} (уровень {level}):\n"
            f"{diagnosis}!"
        )

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /dg"""
    try:
        user = update.effective_user
        args = context.args or []
        
        # Парсинг аргументов
        target = user
        level = 2
        custom_user = False
        
        for arg in args:
            if arg.startswith("@"):
                # Поиск пользователя по юзернейму
                username = arg[1:].lower()
                members = chat_data.members.get(update.effective_chat.id, [])
                found_user = next(
                    (u for u in members 
                     if u.username and u.username.lower() == username),
                    None
                )
                if found_user:
                    target = found_user
                    custom_user = True
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Форматирование имени
        username = (
            f"@{target.username}" 
            if target.username 
            else target.full_name
        )
        if custom_user and not target.username:
            username = f"@{username}"  # Добавляем @ для явного указания

        # Генерация диагноза
        data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        await update.message.reply_text(
            f"🔍 Диагноз для {username} (уровень {level}):\n"
            f"{diagnosis}!"
        )

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    handlers = [
        CommandHandler("start", start),
        CommandHandler("dg", diagnose),
        CommandHandler("random_dg", random_diagnose),
        ChatMemberHandler(handle_chat_event),
        ChatJoinRequestHandler(handle_chat_event)
    ]
    
    application.add_handlers(handlers)
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    if not TOKEN:
        logger.error("❌ Укажите BOT_TOKEN в переменных окружения!")
        exit(1)
    main()
