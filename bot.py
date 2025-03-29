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
    """Класс для управления данными чата"""
    def __init__(self):
        self.members = {}
        self.last_update = {}

    async def update_members(self, chat_id: int, bot, force: bool = False):
        """Основной метод обновления участников"""
        try:
            logger.info(f"🔄 Начало обновления для чата {chat_id}")
            
            # Всегда обновляем при принудительном запросе
            if not force and not self.needs_update(chat_id):
                return

            # Проверка прав администратора
            is_admin = await self._is_admin(bot, chat_id)
            members = []

            if is_admin:
                logger.info("🔐 Используем метод администратора")
                async for member in bot.get_chat_members(chat_id):
                    user = member.user
                    if not user.is_bot:
                        members.append(user)
                        logger.info(f"👤 Добавлен: {user.username or user.full_name}")
            else:
                logger.warning("⚠️ Используем резервный метод")
                async for message in bot.get_chat_history(chat_id, limit=200):
                    user = message.from_user
                    if user and not user.is_bot and user not in members:
                        members.append(user)

            self.members[chat_id] = members
            self.last_update[chat_id] = datetime.now()
            logger.info(f"✅ Успешно обновлено: {len(members)} участников")

        except Exception as e:
            logger.error(f"🚨 Ошибка обновления: {str(e)}")
            await self._fallback_update(chat_id, bot)

    async def _is_admin(self, bot, chat_id: int) -> bool:
        """Проверка прав администратора"""
        try:
            me = await bot.get_me()
            admins = await bot.get_chat_administrators(chat_id)
            return any(admin.user.id == me.id for admin in admins)
        except Exception as e:
            logger.error(f"❌ Ошибка проверки прав: {str(e)}")
            return False

    def needs_update(self, chat_id: int) -> bool:
        """Проверка необходимости обновления"""
        last = self.last_update.get(chat_id)
        return not last or (datetime.now() - last) > timedelta(minutes=30)

chat_data = ChatData()

async def handle_chat_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик событий чата"""
    try:
        chat_id = update.effective_chat.id
        await chat_data.update_members(chat_id, context.bot)
    except Exception as e:
        logger.error(f"Ошибка обработки события: {str(e)}")

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительное обновление списка участников"""
    try:
        chat_id = update.effective_chat.id
        await chat_data.update_members(chat_id, context.bot, force=True)
        
        members = chat_data.members.get(chat_id, [])
        member_list = "\n".join([f"• {m.username or m.full_name}" for m in members]) or "Пусто"
        
        await update.message.reply_text(
            f"🔄 Обновлено участников: {len(members)}\n"
            f"Список:\n{member_list}"
        )
    except Exception as e:
        logger.error(f"Ошибка обновления: {str(e)}")
        await update.message.reply_text("🚨 Ошибка обновления списка")

async def self_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Диагноз для себя"""
    try:
        user = update.effective_user
        args = context.args or []
        level = 2

        # Парсинг уровня
        for arg in args:
            if arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        await update.message.reply_text(
            f"🩺 Диагноз для @{user.username} (уровень {level}):\n"
            f"{diagnosis}!"
        )
    except Exception as e:
        logger.error(f"Ошибка диагноза: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

async def user_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Диагноз для другого пользователя"""
    try:
        chat = update.effective_chat
        args = context.args or []
        
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("🚫 Команда работает только в группах!")
            return

        await chat_data.update_members(chat.id, context.bot)
        members = chat_data.members.get(chat.id, [])

        # Поиск целевого пользователя
        target_user = None
        level = 2
        
        for arg in args:
            if arg.startswith("@"):
                search_username = arg[1:].lower()
                target_user = next(
                    (u for u in members 
                     if u.username and u.username.lower() == search_username),
                    None
                )
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден!")
            return

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
        logger.error(f"Ошибка диагноза: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    help_text = (
        "👨⚕️ Бот-диагност\n\n"
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/diagnose [уровень] - ваш диагноз\n"
        "/dg @юзер [уровень] - диагноз для участника\n"
        "/rf - обновить список участников\n\n"
        "Примеры:\n"
        "/diagnose 3 - ваш диагноз уровня 3\n"
        "/dg @user 2 - диагноз уровня 2 для @user"
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
        logger.error("❌ Требуется переменная окружения BOT_TOKEN!")
        exit(1)
    main()
