import os
import random
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ChatType

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Конфигурация
TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

if not TOKEN or not WEBHOOK_URL:
    logger.error("Не заданы переменные окружения!")
    exit(1)

# Инициализация бота
application = Application.builder().token(TOKEN).build()

# База диагнозов (обновленная структура)
DIAGNOSIS_DATA = {
    1: {
        "problems": [
            "покраснение {body_part} {severity}",
            "зуд {body_part} {severity}",
            "легкое недомогание {body_part} {severity}"
        ],
        "body_parts": ["уха", "носа", "пальца"],
        "severity": ["начальной стадии", "легкой формы"]
    },
    2: {
        "problems": [
            "паралич {body_part} {severity}",
            "гастрит {body_part} {severity}",
            "пародонтоз {body_part} {severity}"
        ],
        "body_parts": ["ребра", "колена", "локтя"],
        "severity": ["второй степени", "средней тяжести"]
    },
    3: {
        "problems": [
            "недоразвитие {body_part} {severity}",
            "гипертрофия {body_part} {severity}",
            "дегенерация {body_part} {severity}"
        ],
        "body_parts": ["гипоталамуса", "селезенки", "надкостницы"],
        "severity": ["терминальной стадии", "с осложнениями"],
        "modifiers": ["внезапного происхождения", "с метастазами"]
    }
}

def generate_diagnosis(level: int) -> str:
    """Генерация диагноза с правильным склонением"""
    level = max(1, min(3, level))
    data = DIAGNOSIS_DATA[level]
    
    # Выбираем случайный шаблон проблемы
    problem_template = random.choice(data["problems"])
    
    # Выбираем части тела и степень
    body_part = random.choice(data["body_parts"])
    severity = random.choice(data["severity"])
    
    # Формируем диагноз
    diagnosis = problem_template.format(
        body_part=body_part,
        severity=severity
    )
    
    # Добавляем модификаторы для 3 уровня
    if level == 3 and random.random() < 0.5:
        diagnosis += " " + random.choice(data["modifiers"])
    
    return diagnosis

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    help_text = (
        "🔮 Бот-диагност для чатов!\n"
        "Добавьте меня в группу и используйте:\n"
        "/diagnose [1-3] - случайный диагноз участнику\n"
        "Примеры:\n"
        "/diagnose - средняя сложность\n"
        "/diagnose 3 - максимальная жесткость"
    )
    await update.message.reply_text(help_text)

async def get_random_member(chat_id: int):
    """Получает случайного участника чата"""
    try:
        members = []
        async for member in application.bot.get_chat_members(chat_id):
            user = member.user
            if not user.is_bot and (user.username or user.first_name):
                members.append(user)
        return random.choice(members) if members else None
    except Exception as e:
        logger.error(f"Ошибка получения участников: {e}")
        return None

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /diagnose"""
    try:
        if update.effective_chat.type == ChatType.PRIVATE:
            await update.message.reply_text("❌ Работает только в групповых чатах!")
            return

        # Определяем уровень сложности
        level = int(context.args[0]) if context.args else 2
        level = max(1, min(3, level))

        # Выбираем случайного участника
        user = await get_random_member(update.effective_chat.id)
        if not user:
            await update.message.reply_text("😢 Нет подходящих пользователей!")
            return

        # Генерируем диагноз
        diagnosis = generate_diagnosis(level)
        
        # Формируем ответ
        username = f"@{user.username}" if user.username else user.first_name
        response = f"⚠️ Диагностика выявила:\nу {username} {diagnosis.capitalize()}!"
        
        await update.message.reply_text(response)

    except (ValueError, IndexError):
        await update.message.reply_text("⚠️ Используйте: /diagnose [1-3]")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("🚨 Ошибка диагностики, попробуйте позже")

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
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
        logger.error(f"Webhook error: {e}")
        return '', 500

@app.route('/')
def health_check():
    return "Diagnosis Bot API", 200

if __name__ == '__main__':
    application.run_webhook(
        listen='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/webhook",
        drop_pending_updates=True
)
