import os
import random
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv('TELEGRAM_TOKEN')

# База диагнозов
DIAGNOSIS_DB = {
    1: {'problems': ['Покраснение', 'Зуд', 'Икота'], 'parts': ['уха', 'носа', 'пальца'], 'severity': ['лёгкой формы']},
    2: {'problems': ['Паралич', 'Гастрит', 'Аритмия'], 'parts': ['ребра', 'колена', 'селезёнки'], 'severity': ['средней тяжести']},
    3: {'problems': ['Гангрена', 'Дегенерация', 'Тромбоз'], 'parts': ['гипоталамуса', 'надкостницы', 'яичка'], 'severity': ['терминальной стадии']}
}

async def get_chat_members(chat_id, bot):
    """Получаем всех участников чата с обработкой исключений"""
    try:
        members = []
        count = 0
        async for member in bot.get_chat_members(chat_id):
            user = member.user
            count += 1
            logger.info(f"Найден пользователь {count}: ID={user.id}, Username={user.username}, IsBot={user.is_bot}")
            
            if not user.is_bot:
                members.append(user)
        
        logger.info(f"Всего найдено участников: {len(members)}")
        return members
    except Exception as e:
        logger.error(f"Ошибка при получении участников: {e}")
        return []

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный обработчик команды /diagnose"""
    try:
        chat = update.effective_chat
        logger.info(f"Обработка чата: ID={chat.id}, Тип={chat.type}")
        
        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("❌ Я работаю только в группах!")
            return

        # Получаем всех участников с подробным логированием
        members = await get_chat_members(chat.id, context.bot)
        
        if not members:
            await update.message.reply_text("😢 Не могу найти ни одного пользователя! Проверьте, что:\n"
                                          "1. Я добавлен как администратор\n"
                                          "2. В чате есть обычные пользователи\n"
                                          "3. У пользователей есть usernames")
            return

        # Выбираем случайного пользователя
        user = random.choice(members)
        username = f"@{user.username}" if user.username else user.first_name
        logger.info(f"Выбран пользователь: {username}")

        # Генерируем диагноз
        level = int(context.args[0]) if context.args else 2
        level = max(1, min(3, level))
        
        data = DIAGNOSIS_DB[level]
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        )

        await update.message.reply_text(
            f"🔍 Результат для {username}:\n"
            f"Диагноз: {diagnosis.capitalize()}!"
        )

    except Exception as e:
        logger.error(f"Ошибка в команде /diagnose: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка, попробуйте позже")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🩺 Бот-диагност для групп!\n"
        "Добавьте меня в группу и используйте:\n"
        "/diagnose [1-3] - случайный диагноз участнику\n\n"
        "Убедитесь, что:\n"
        "1. Я администратор в чате\n"
        "2. В чате есть обычные пользователи"
    )

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("diagnose", diagnose))
    
    logger.info("Бот запущен в режиме polling...")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Не задан TELEGRAM_TOKEN!")
        exit(1)
    main()
