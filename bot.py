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
    """Класс для отслеживания участников чата"""
    def __init__(self):
        self.chat_data = {}

    async def update_members(self, chat_id: int, bot):
        """Обновление списка участников через API"""
        try:
            members = []
            async for member in bot.get_chat_members(chat_id):
                if not member.user.is_bot:
                    members.append(member.user)
            self.chat_data[chat_id] = members
            logger.info(f"Обновлены участники чата {chat_id}")
        except Exception as e:
            logger.error(f"Ошибка обновления: {str(e)}")

    def get_random_member(self, chat_id: int):
        """Получение случайного участника"""
        members = self.chat_data.get(chat_id, [])
        return random.choice(members) if members else None

tracker = ChatTracker()

async def handle_chat_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик изменений в чате"""
    chat_id = update.effective_chat.id
    await tracker.update_members(chat_id, context.bot)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инициализация бота в чате"""
    chat_id = update.effective_chat.id
    await tracker.update_members(chat_id, context.bot)
    
    text = (
        "👨⚕️ Медицинский бот-диагност\n\n"
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/diagnose [@юзер] [уровень] - поставить диагноз\n"
        "/dg [@юзер] [уровень] - сокращенная команда\n\n"
        "Примеры:\n"
        "/dg @user123 3\n"
        "/diagnose 2"
    )
    await update.message.reply_text(text)

async def diagnose_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основная логика диагноза"""
    try:
        chat = update.effective_chat
        args = context.args or []
        
        # Проверка типа чата
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("⚠️ Эта команда работает только в группах!")
            return

        # Парсинг аргументов
        level = 2
        target_username = None
        
        for arg in args:
            if arg.startswith("@"):
                target_username = arg[1:]  # Убираем @ для поиска
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Определение пользователя
        if target_username:
            # Поиск по username
            member = next(
                (m for m in tracker.chat_data.get(chat.id, []) 
                 if m.username and m.username.lower() == target_username.lower()),
                None
            )
            username = f"@{target_username}"
        else:
            # Случайный выбор
            member = tracker.get_random_member(chat.id)
            username = (
                f"@{member.username}" 
                if member and member.username 
                else (member.full_name if member else "Случайный участник")
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
        await update.message.reply_text("⚠️ Произошла ошибка при выполнении команды")

def main():
    # Создаем и настраиваем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    handlers = [
        CommandHandler(["start", "help"], start),
        CommandHandler(["diagnose", "dg"], diagnose_command),
        ChatMemberHandler(handle_chat_updates),
        ChatJoinRequestHandler(handle_chat_updates)
    ]
    
    application.add_handlers(handlers)
    
    # Запускаем бота
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    if not TOKEN:
        logger.error("❌ Требуется переменная окружения BOT_TOKEN!")
        exit(1)
    main()
