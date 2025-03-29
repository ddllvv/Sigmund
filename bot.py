import os
import random
import logging
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

class ChatTracker:
    """Класс для управления участниками чата"""
    def __init__(self):
        self.chat_members = {}

    async def update_members(self, chat_id: int, bot):
        """Обновление списка участников"""
        try:
            members = []
            async for member in bot.get_chat_members(chat_id):
                if not member.user.is_bot:
                    members.append(member.user)
            self.chat_members[chat_id] = members
            logger.info(f"Обновлен список участников для чата {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка обновления: {str(e)}")

    def get_random_member(self, chat_id: int):
        """Получение случайного участника"""
        members = self.chat_members.get(chat_id, [])
        return random.choice(members) if members else None

tracker = ChatTracker()

async def handle_chat_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик событий чата"""
    chat_id = update.effective_chat.id
    await tracker.update_members(chat_id, context.bot)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициализация бота в чате"""
    chat_id = update.effective_chat.id
    await tracker.update_members(chat_id, context.bot)
    await update.message.reply_text(
        "👨⚕️ Бот-диагност активирован!\n"
        "Используйте /dg [@юзер] [уровень 1-3]\n"
        "Пример: /dg @user 2"
    )

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды диагноза"""
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
            if arg.startswith("@"):
                target_username = arg[1:].lower()
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Выбор пользователя
        selected_member = None
        
        if target_username:
            # Поиск по username
            selected_member = next(
                (m for m in tracker.chat_members.get(chat.id, []) 
                 if m.username and m.username.lower() == target_username),
                None
            )
        else:
            # Случайный выбор из участников
            selected_member = tracker.get_random_member(chat.id)
        
        # Fallback: если не нашли, используем отправителя
        if not selected_member:
            selected_member = user

        # Форматирование имени
        username = (
            f"@{selected_member.username}" 
            if selected_member.username 
            else selected_member.full_name
        )

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
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dg", diagnose))
    application.add_handler(ChatMemberHandler(handle_chat_events))
    application.add_handler(ChatJoinRequestHandler(handle_chat_events))
    
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    if not TOKEN:
        logger.error("❌ Укажите BOT_TOKEN в переменных окружения!")
        exit(1)
    main()
