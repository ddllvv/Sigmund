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
    """Управление данными чата в памяти"""
    def __init__(self):
        self.members = {}
        self.last_update = {}

    async def update_members(self, chat_id: int, bot, force: bool = False):
        """Обновление списка участников"""
        try:
            if not force and not self.needs_update(chat_id):
                return

            # Основной метод для администраторов
            if await self._is_admin(bot, chat_id):
                members = []
                async for member in bot.get_chat_members(chat_id):
                    if not member.user.is_bot:
                        members.append(member.user)
                self.members[chat_id] = members
            else:
                # Резервный метод через историю сообщений
                members = []
                async for message in bot.get_chat_history(chat_id, limit=100):
                    user = message.from_user
                    if user and not user.is_bot and user not in members:
                        members.append(user)
                self.members[chat_id] = members

            self.last_update[chat_id] = datetime.now()
            logger.info(f"Обновлены участники чата {chat_id}")

        except Exception as e:
            logger.error(f"Ошибка обновления: {str(e)}")

    async def _is_admin(self, bot, chat_id: int) -> bool:
        """Проверка прав администратора"""
        try:
            admins = await bot.get_chat_administrators(chat_id)
            return any(admin.user.id == bot.id for admin in admins)
        except Exception as e:
            logger.error(f"Ошибка проверки прав: {str(e)}")
            return False

    def needs_update(self, chat_id: int) -> bool:
        """Нужно ли обновлять данные"""
        last = self.last_update.get(chat_id)
        return not last or (datetime.now() - last) > timedelta(minutes=30)

    def get_member_list(self, chat_id: int) -> list:
        """Получение списка участников"""
        return self.members.get(chat_id, [])

chat_data = ChatData()

async def handle_chat_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик событий чата"""
    chat_id = update.effective_chat.id
    await chat_data.update_members(chat_id, context.bot)

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительное обновление списка участников"""
    try:
        chat_id = update.effective_chat.id
        await chat_data.update_members(chat_id, context.bot, force=True)
        
        members = chat_data.get_member_list(chat_id)
        member_list = "\n".join([f"• {m.username or m.full_name}" for m in members])
        
        await update.message.reply_text(
            f"🔄 Список обновлен! Участников: {len(members)}\n"
            f"Список:\n{member_list}"
        )
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка обновления")

async def self_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Диагноз для себя"""
    try:
        user = update.effective_user
        args = context.args or []
        
        # Парсинг уровня
        level = 2
        for arg in args:
            if arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Генерация диагноза
        data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        username = f"@{user.username}" if user.username else user.full_name
        await update.message.reply_text(
            f"🩺 Ваш диагноз (уровень {level}):\n"
            f"{diagnosis}!"
        )

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

async def user_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Диагноз для другого пользователя"""
    try:
        chat = update.effective_chat
        args = context.args or []
        
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("🚫 Только в группах!")
            return

        await chat_data.update_members(chat.id, context.bot)
        members = chat_data.get_member_list(chat.id)

        # Поиск целевого пользователя
        target_user = None
        level = 2
        
        for arg in args:
            if arg.startswith("@"):
                # Поиск по username
                search_username = arg[1:].lower()
                target_user = next(
                    (u for u in members 
                     if u.username and u.username.lower() == search_username),
                    None
                )
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        if not target_user:
            await update.message.reply_text("❌ Укажите существующего @пользователя")
            return

        # Генерация диагноза
        data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        username = f"@{target_user.username}" if target_user.username else target_user.full_name
        await update.message.reply_text(
            f"🔍 Диагноз для {username} (уровень {level}):\n"
            f"{diagnosis}!"
        )

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    help_text = (
        "👨⚕️ Бот-диагност\n\n"
        "Команды:\n"
        "/diagnose [уровень] - диагноз себе\n"
        "/dg @юзер [уровень] - диагноз другому\n"
        "/rf - обновить список участников\n"
        "\nПримеры:\n"
        "/diagnose 3 - ваш диагноз уровня 3\n"
        "/dg @user 1 - диагноз для @user\n"
        "/rf - показать всех участников"
    )
    await update.message.reply_text(help_text)

def main():
    application = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    handlers = [
        CommandHandler("start", start),
        CommandHandler("diagnose", self_diagnose),
        CommandHandler("dg", user_diagnose),
        CommandHandler("rf", refresh),
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
