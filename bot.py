import os
import random
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Получаем токен из переменных окружения
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    logger.error("Токен Telegram не найден! Убедитесь, что переменная TELEGRAM_TOKEN установлена")
    exit(1)

# Создаем приложение Telegram Bot
application = Application.builder().token(TOKEN).build()

# База данных диагнозов (уровни 1-3)
DIAGNOSIS_DATA = {
    1: {
        "diseases": ["Покраснение", "Зуд", "Легкое недомогание", "Икота"],
        "body_parts": ["уха", "носа", "пальца"],
        "severity": ["начальной стадии", "легкой формы"]
    },
    2: {
        "diseases": ["Паралич", "Гастрит", "Пародонтоз", "Аритмия"],
        "body_parts": ["ребра", "колена", "локтя"],
        "severity": ["второй степени", "средней тяжести"]
    },
    3: {
        "diseases": ["Недоразвитие", "Гипертрофия", "Дегенерация", "Тромбоз"],
        "body_parts": ["гипоталамуса", "селезенки", "надкостницы"],
        "severity": ["терминальной стадии", "с осложнениями"],
        "modifiers": ["внезапного происхождения", "с метастазами"]
    }
}

def generate_diagnosis(level: int):
    """Генерирует случайный диагноз для указанного уровня"""
    level = max(1, min(3, level))  # Ограничиваем уровень 1-3
    level_data = DIAGNOSIS_DATA[level]
    
    diagnosis = (
        f"{random.choice(level_data['diseases'])} "
        f"{random.choice(level_data['body_parts'])} "
        f"{random.choice(level_data['severity'])}"
    )
    
    if level == 3 and random.random() < 0.5:
        diagnosis += f", {random.choice(level_data['modifiers'])}"
    
    return diagnosis

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /diagnose"""
    try:
        # Пытаемся получить уровень из аргументов (по умолчанию 2)
        level = int(context.args[0]) if context.args else 2
    except (ValueError, IndexError):
        level = 2
    
    # Логируем запрос
    logger.info(f"Получен запрос от {update.effective_user.id} с уровнем {level}")
    
    # Генерируем и отправляем диагноз
    diagnosis = generate_diagnosis(level)
    response = f"🔍 Результат (уровень {level}):\n{diagnosis}"
    await update.message.reply_text(response)

# Регистрируем обработчик команд
application.add_handler(CommandHandler("diagnose", diagnose))

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Endpoint для вебхука Telegram"""
    try:
        # Получаем и обрабатываем обновление
        update = Update.de_json(await request.get_json(), application.bot)
        await application.update_queue.put(update)
        return '', 200
    except Exception as e:
        logger.error(f"Ошибка обработки запроса: {e}")
        return '', 500

@app.route('/')
def index():
    """Проверочная страница"""
    return 'Telegram Diagnosis Bot is running!'

if __name__ == '__main__':
    # Конфигурация для Render
    PORT = int(os.environ.get('PORT', 5000))
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')
    
    if WEBHOOK_URL:
        # Режим вебхука (продакшен)
        application.run_webhook(
            listen='0.0.0.0',
            port=PORT,
            url_path=TOKEN,
            webhook_url=f'{WEBHOOK_URL}/webhook'
        )
    else:
        # Локальный режим (для тестирования)
        application.run_polling()
