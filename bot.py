import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация данных для диагнозов
DIAGNOSIS_DATA = {
    "diseases": {
        "мягкий": ["Покраснение", "Зуд", "Легкое недомогание", "Икота"],
        "средний": ["Паралич", "Гастрит", "Пародонтоз", "Аритмия"],
        "жесткий": ["Недоразвитие", "Гипертрофия", "Дегенерация", "Тромбоз"]
    },
    "body_parts": {
        "мягкий": ["уха", "носа", "пальца"],
        "средний": ["ребра", "колена", "локтя"],
        "жесткий": ["гипоталамуса", "селезенки", "надкостницы"]
    },
    "severity": {
        "мягкий": ["начальной стадии", "легкой формы"],
        "средний": ["второй степени", "средней тяжести"],
        "жесткий": ["терминальной стадии", "с осложнениями"]
    },
    "modifiers": {
        "жесткий": ["внезапного происхождения", "с метастазами"]
    }
}

app = Flask(__name__)
application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

# Генератор диагнозов
def generate_diagnosis(severity_level):
    import random
    
    disease = random.choice(DIAGNOSIS_DATA["diseases"][severity_level])
    body_part = random.choice(DIAGNOSIS_DATA["body_parts"][severity_level])
    severity = random.choice(DIAGNOSIS_DATA["severity"][severity_level])
    
    modifier = ""
    if severity_level == "жесткий" and random.random() < 0.5:
        modifier = ", " + random.choice(DIAGNOSIS_DATA["modifiers"]["жесткий"])
    
    templates = [
        f"{disease} {body_part} {severity}{modifier}",
        f"Диагноз: {disease} {body_part}{modifier} ({severity})"
    ]
    
    return random.choice(templates)

# Получение случайного пользователя
async def get_random_member(chat_id, context):
    members = []
    async for member in context.bot.get_chat_members(chat_id):
        if not member.user.is_bot:
            members.append(member.user)
    return random.choice(members) if members else None

# Обработчик команды /diagnose
async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    severity_level = "средний"
    if context.args:
        level = context.args[0].lower()
        if level in ["мягкий", "средний", "жесткий"]:
            severity_level = level
    
    user = await get_random_member(update.effective_chat.id, context)
    if not user:
        await update.message.reply_text("В чате нет пользователей 😢")
        return
    
    diagnosis = generate_diagnosis(severity_level)
    response = f"🔍 Результат обследования для @{user.username}:\n{diagnosis}"
    await update.message.reply_text(response)

# Регистрация обработчиков
application.add_handler(CommandHandler("diagnose", diagnose))

# Вебхук для PythonAnywhere
@app.route('/' + os.getenv('TELEGRAM_TOKEN'), methods=['POST'])
async def webhook():
    await application.update_queue.put(
        Update.de_json(data=request.json, bot=application.bot)
    return 'ok', 200

@app.route('/')
def index():
    return 'Diagnosis Bot is running!'

if __name__ == '__main__':
    # Настройка вебхука при первом запуске
    if not os.getenv('PYTHONANYWHERE_DOMAIN'):
        # Локальный запуск
        application.run_polling()
    else:
        # Запуск на PythonAnywhere
        domain = os.getenv('PYTHONANYWHERE_DOMAIN')
        application.run_webhook(
            listen='0.0.0.0',
            port=5000,
            url_path=os.getenv('TELEGRAM_TOKEN'),
            webhook_url=f'https://{domain}/{os.getenv('TELEGRAM_TOKEN')}'
)
