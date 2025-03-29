import os
import random
import logging
from telegram import Update
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

async def get_chat_members(bot, chat_id):
    """Получение списка участников (исключая ботов)"""
    try:
        members = []
        async for member in bot.get_chat_members(chat_id):
            if not member.user.is_bot:
                members.append(member.user)
        return members
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    help_text = (
        "👨⚕️ Бот-диагност\n\n"
        "Команды:\n"
        "/dg [@юзер] [уровень] - диагноз пользователю\n"
        "/random_dg [уровень] - случайному участнику\n"
        "\nПримеры:\n"
        "/random_dg 3 - случайный участник с уровнем 3\n"
        "/dg @user 1 - диагноз уровня 1 для @user"
    )
    await update.message.reply_text(help_text)

async def random_diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /random_dg"""
    try:
        chat = update.effective_chat
        args = context.args or []
        
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("🚫 Только в группах!")
            return

        # Получаем участников
        members = await get_chat_members(context.bot, chat.id)
        if not members:
            await update.message.reply_text("😢 Нет участников для диагностики")
            return

        # Парсинг уровня
        level = 2
        for arg in args:
            if arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Выбираем случайного участника
        random_user = random.choice(members)
        username = f"@{random_user.username}" if random_user.username else random_user.full_name

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
        
        # Изначально цель - отправитель
        target_username = user.username or user.full_name
        display_name = f"@{user.username}" if user.username else user.full_name
        level = 2

        # Парсинг аргументов
        for arg in args:
            if arg.startswith("@"):
                target_username = arg
                display_name = arg
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

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

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dg", diagnose))
    application.add_handler(CommandHandler("random_dg", random_diagnose))
    
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    if not TOKEN:
        logger.error("❌ Укажите BOT_TOKEN в переменных окружения!")
        exit(1)
    main()
