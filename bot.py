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

# Конфигурация
TOKEN = os.getenv('TELEGRAM_TOKEN')

# База диагнозов
DIAGNOSIS_DB = {
    1: {
        'problems': ['Покраснение', 'Зуд', 'Икота'],
        'parts': ['уха', 'носа', 'пальца'],
        'severity': ['лёгкой формы', 'начальной стадии']
    },
    2: {
        'problems': ['Паралич', 'Гастрит', 'Аритмия'],
        'parts': ['ребра', 'колена', 'селезёнки'],
        'severity': ['средней тяжести', 'острой формы']
    },
    3: {
        'problems': ['Гангрена', 'Дегенерация', 'Тромбоз'],
        'parts': ['гипоталамуса', 'надкостницы', 'яичка'],
        'severity': ['терминальной стадии', 'с метастазами']
    }
}

async def get_random_member(chat_id, bot):
    """Получает случайного участника чата"""
    try:
        members = []
        async for member in bot.get_chat_members(chat_id):
            user = member.user
            if not user.is_bot and (user.username or user.first_name):
                members.append(user)
        return random.choice(members) if members else None
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        return None

async def generate_diagnosis(level: int) -> str:
    """Генерирует случайный диагноз"""
    level = max(1, min(3, level))
    data = DIAGNOSIS_DB[level]
    return (
        f"{random.choice(data['problems'])} "
        f"{random.choice(data['parts'])} "
        f"{random.choice(data['severity'])}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    help_text = (
        "🩺 Бот-диагност для групп!\n"
        "Добавьте меня в группу и используйте:\n"
        "/diagnose [1-3] - случайный диагноз участнику\n"
        "Пример: /diagnose 3"
    )
    await update.message.reply_text(help_text)

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /diagnose"""
    try:
        # Проверка типа чата
        if update.effective_chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("❌ Работаю только в группах!")
            return

        # Получаем случайного пользователя
        user = await get_random_member(
            update.effective_chat.id, 
            context.bot
        )
        if not user:
            await update.message.reply_text("😢 Нет подходящих пользователей!")
            return

        # Определяем уровень сложности
        try:
            level = int(context.args[0]) if context.args else 2
        except:
            level = 2
        level = max(1, min(3, level))

        # Генерируем диагноз
        diagnosis = await generate_diagnosis(level)
        username = f"@{user.username}" if user.username else user.first_name

        # Отправляем результат
        await update.message.reply_text(
            f"🔍 Результат для {username}:\n"
            f"Диагноз: {diagnosis.capitalize()}!"
        )

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка, попробуйте позже")

def main():
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("diagnose", diagnose))

    # Запускаем бота
    logger.info("Бот запущен в режиме polling...")
    application.run_polling()

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Не задан TELEGRAM_TOKEN!")
        exit(1)
    main()
