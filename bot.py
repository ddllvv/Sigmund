import os
import random
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Проверка переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

if not TELEGRAM_TOKEN or not WEBHOOK_URL:
    logger.error("Требуются TELEGRAM_TOKEN и WEBHOOK_URL!")
    exit(1)

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)
application = Application.builder().token(TELEGRAM_TOKEN).build()

# База диагнозов
DIAGNOSIS_DB = {
    1: {
        "problems": ["Паралич", "Гастрит", "Пародонтоз"],
        "parts": ["уха", "яичка", "пальца"],
        "severity": ["лёгкой формы", "начальной стадии"]
    },
    2: {
        "problems": ["Тромбоз", "Аритмия", "Недоразвитие"],
        "parts": ["ребра", "колена", "селезёнки"],
        "severity": ["средней тяжести", "острой формы"]
    },
    3: {
        "problems": ["Гангрена", "Дегенерация", "Гипертрофия"],
        "parts": ["гипоталамуса", "надкостницы", "лимфоузла"],
        "severity": ["терминальной стадии", "с метастазами"]
    }
}

async def get_random_member(chat_id):
    """Получает случайного пользователя чата"""
    try:
        members = []
        async for member in bot.get_chat_members(chat_id):
            if not member.user.is_bot:
                members.append(member.user)
        return random.choice(members) if members else None
    except Exception as e:
        logger.error(f"Ошибка получения участников: {e}")
        return None

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /diagnose"""
    try:
        # Выбираем случайного пользователя
        user = await get_random_member(update.effective_chat.id)
        if not user:
            await update.message.reply_text("😢 Нет пользователей для диагностики!")
            return

        # Определяем уровень сложности
        try:
            level = int(context.args[0]) if context.args else 2
            level = max(1, min(3, level))
        except:
            level = 2

        # Генерируем диагноз
        data = DIAGNOSIS_DB[level]
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        )

        # Отправляем результат
        username = f"@{user.username}" if user.username else user.first_name
        await update.message.reply_text(
            f"🔍 Результат диагностики:\n"
            f"У {username} обнаружено: {diagnosis}!"
        )

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка, попробуйте позже")

# Регистрируем обработчики
application.add_handler(CommandHandler("diagnose", diagnose))

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Обработчик вебхука"""
    try:
        data = await request.get_json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return '', 200
    except Exception as e:
        logger.error(f"Ошибка вебхука: {e}")
        return '', 500

if __name__ == '__main__':
    # Настройка вебхука
    application.run_webhook(
        listen='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/webhook"
)
