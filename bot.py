import os
import random
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('BOT_TOKEN')

DIAGNOSIS_DATA = {
    1: {
        'problems': ['Покраснение', 'Зуд', 'Икота'],
        'parts': ['уха', 'носа', 'пальца'],
        'severity': ['начальной стадии']
    },
    2: {
        'problems': ['Паралич', 'Гастрит', 'Аритмия'],
        'parts': ['ребра', 'колена', 'селезёнки'],
        'severity': ['средней тяжести']
    },
    3: {
        'problems': ['Гангрена', 'Дегенерация', 'Тромбоз'],
        'parts': ['гипоталамуса', 'надкостницы', 'яичка'],
        'severity': ['терминальной стадии']
    }
}

async def get_chat_members(bot, chat_id):
    """Безопасное получение участников через Bot API"""
    try:
        members = []
        async for member in bot.get_chat_members(chat_id):
            if not member.user.is_bot:
                members.append(member.user)
        return members
    except Exception as e:
        logger.error(f"Ошибка получения участников: {str(e)}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    await update.message.reply_text(
        "👨⚕️ Бот-диагност для групп\n\n"
        "Команды:\n"
        "/diagnose [@юзер] [уровень 1-3]\n"
        "Примеры:\n"
        "/diagnose 2 - случайному участнику\n"
        "/diagnose @username 3"
    )

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /diagnose"""
    try:
        chat = update.effective_chat
        args = context.args or []
        
        # Проверка типа чата
        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("🚫 Работает только в группах!")
            return

        # Получаем участников
        members = await get_chat_members(context.bot, chat.id)
        if not members:
            await update.message.reply_text("😢 Нет участников для диагностики")
            return

        # Парсинг аргументов
        level = 2
        target_user = None
        
        for arg in args:
            if arg.startswith('@'):
                username = arg[1:].lower()
                target_user = next((u for u in members if u.username and u.username.lower() == username), None)
            elif arg.isdigit():
                level = max(1, min(3, int(arg)))

        # Выбор пользователя
        user = target_user or random.choice(members)
        username = f"@{user.username}" if user.username else user.first_name

        # Генерация диагноза
        data = DIAGNOSIS_DATA[max(1, min(3, level))]
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        )

        await update.message.reply_text(
            f"🔍 Диагноз для {username} (уровень {level}):\n"
            f"{diagnosis.capitalize()}!"
        )

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("diagnose", diagnose))
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    if not TOKEN:
        logger.error("❌ Требуется переменная BOT_TOKEN!")
        exit(1)
    main()
