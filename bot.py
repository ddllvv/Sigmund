import os
import random
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
application = Application.builder().token(TOKEN).build()

# База данных диагнозов с числовыми уровнями
DIAGNOSIS_DATA = {
    "diseases": {
        1: ["Покраснение", "Зуд", "Легкое недомогание", "Икота"],
        2: ["Паралич", "Гастрит", "Пародонтоз", "Аритмия"],
        3: ["Недоразвитие", "Гипертрофия", "Дегенерация", "Тромбоз"]
    },
    "body_parts": {
        1: ["уха", "носа", "пальца"],
        2: ["ребра", "колена", "локтя"],
        3: ["гипоталамуса", "селезенки", "надкостницы"]
    },
    "severity": {
        1: ["начальной стадии", "легкой формы"],
        2: ["второй степени", "средней тяжести"],
        3: ["терминальной стадии", "с осложнениями"]
    },
    "modifiers": {
        3: ["внезапного происхождения", "с метастазами"]
    }
}

def generate_diagnosis(level: int):
    """Генерирует диагноз для указанного уровня"""
    level = max(1, min(3, level))  # Ограничение уровня 1-3
    
    disease = random.choice(DIAGNOSIS_DATA["diseases"][level])
    body_part = random.choice(DIAGNOSIS_DATA["body_parts"][level])
    severity = random.choice(DIAGNOSIS_DATA["severity"][level])
    
    modifier = ""
    if level == 3 and random.random() < 0.5:
        modifier = ", " + random.choice(DIAGNOSIS_DATA["modifiers"][3])
    
    templates = [
        f"{disease} {body_part} {severity}{modifier}",
        f"Диагноз: {disease} {body_part}{modifier} ({severity})"
    ]
    return random.choice(templates)

async def get_random_member(chat_id, context):
    members = []
    async for member in context.bot.get_chat_members(chat_id):
        if not member.user.is_bot:
            members.append(member.user)
    return random.choice(members) if members else None

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        level = int(context.args[0]) if context.args else 2
    except (ValueError, IndexError):
        level = 2
    
    user = await get_random_member(update.effective_chat.id, context)
    if not user:
        await update.message.reply_text("В чате нет пользователей 😢")
        return
    
    diagnosis = generate_diagnosis(level)
    response = f"🔍 Результат обследования для @{user.username} (уровень {level}):\n{diagnosis}"
    await update.message.reply_text(response)

# Регистрация обработчиков
application.add_handler(CommandHandler("diagnose", diagnose))

@app.route('/webhook', methods=['POST'])
async def webhook():
    await application.update_queue.put(
        Update.de_json(await request.get_json(), application.bot)
    )
    return '', 200

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    application.run_webhook(
        listen='0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=os.environ.get('WEBHOOK_URL') + '/webhook'
)
