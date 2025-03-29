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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "👨⚕️ Бот-диагност для групп\n\n"
        "Используйте команды:\n"
        "/diagnose или /dg [@юзер] [уровень 1-3]\n"
        "Примеры:\n"
        "/dg 2 - случайный участник\n"
        "/diagnose @username 3"
    )

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный обработчик с обходом ограничений"""
    try:
        chat = update.effective_chat
        args = context.args or []
        
        if chat.type not in ["group", "supergroup"]:
            await update.message.reply_text("🚫 Работает только в группах!")
            return

        # Парсинг аргументов
        level = 2
        target = None
        
        for arg in args:
            if arg.startswith("@"):
                target = arg  # Сохраняем оригинальное упоминание
            elif arg.isdigit() and 1 <= int(arg) <= 3:
                level = int(arg)

        # Если есть упоминание - используем как есть
        if target:
            username = target
        else:
            # Пытаемся найти случайного пользователя из истории чата
            try:
                members = []
                async for message in chat.get_messages(limit=100):
                    user = message.from_user
                    if user and not user.is_bot and user.username:
                        members.append(f"@{user.username}")
                
                if members:
                    username = random.choice(members)
                else:
                    username = "случайного участника"
            except Exception as e:
                username = "случайного участника"
                logger.warning(f"Не удалось получить историю чата: {e}")

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
    application.add_handler(CommandHandler(["diagnose", "dg"], diagnose))
    
    logger.info("Бот запущен...")
    application.run_polling(
        drop_pending_updates=True,  # Решение проблемы Conflict
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    if not TOKEN:
        logger.error("❌ Требуется переменная BOT_TOKEN!")
        exit(1)
    main()
