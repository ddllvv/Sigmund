import os
import random
import logging
import asyncio
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
if not TOKEN:
    logger.error("Не задан TELEGRAM_TOKEN!")
    exit(1)

# Блокировка для предотвращения дублирующих запросов
lock = asyncio.Lock()

# База диагнозов
DIAGNOSIS_DB = {
    1: {'problems': ['Покраснение', 'Зуд', 'Икота'], 'parts': ['уха', 'носа', 'пальца'], 'severity': ['лёгкой формы']},
    2: {'problems': ['Паралич', 'Гастрит', 'Аритмия'], 'parts': ['ребра', 'колена', 'селезёнки'], 'severity': ['средней тяжести']},
    3: {'problems': ['Гангрена', 'Дегенерация', 'Тромбоз'], 'parts': ['гипоталамуса', 'надкостницы', 'яичка'], 'severity': ['терминальной стадии']}
}

async def get_random_member(chat_id, bot):
    """Безопасное получение случайного участника"""
    try:
        members = []
        async for member in bot.get_chat_members(chat_id):
            user = member.user
            if not user.is_bot and (user.username or user.first_name):
                members.append(user)
        return random.choice(members) if members else None
    except Exception as e:
        logger.error(f"Ошибка получения участников: {str(e)}")
        return None

async def generate_diagnosis(level):
    """Генерация диагноза с защитой от ошибок"""
    try:
        level = max(1, min(3, level))
        data = DIAGNOSIS_DB[level]
        return f"{random.choice(data['problems'])} {random.choice(data['parts'])} {random.choice(data['severity'])}"
    except Exception as e:
        logger.error(f"Ошибка генерации диагноза: {str(e)}")
        return "неизвестное заболевание"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        await update.message.reply_text(
            "🩺 Бот-диагност для групп!\n"
            "Используйте /diagnose [1-3]\n"
            "Пример: /diagnose 3"
        )
    except Exception as e:
        logger.error(f"Ошибка в /start: {str(e)}")

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Безопасный обработчик команды /diagnose"""
    async with lock:  # Защита от параллельного выполнения
        try:
            if update.effective_chat.type not in ['group', 'supergroup']:
                await update.message.reply_text("❌ Работаю только в группах!")
                return

            user = await get_random_member(update.effective_chat.id, context.bot)
            if not user:
                await update.message.reply_text("😢 Нет подходящих пользователей!")
                return

            level = int(context.args[0]) if context.args else 2
            diagnosis = await generate_diagnosis(level)
            username = f"@{user.username}" if user.username else user.first_name

            await update.message.reply_text(
                f"🔍 Результат для {username}:\n"
                f"Диагноз: {diagnosis.capitalize()}!"
            )

        except ValueError:
            await update.message.reply_text("⚠️ Используйте: /diagnose [1-3]")
        except Exception as e:
            logger.error(f"Критическая ошибка: {str(e)}")
            await update.message.reply_text("🚨 Произошла ошибка, попробуйте позже")

def main():
    """Запуск бота с защитой от дублирования"""
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("diagnose", diagnose))
        
        logger.info("Запуск бота...")
        application.run_polling(
            drop_pending_updates=True,  # Игнорировать старые сообщения
            allowed_updates=Update.ALL_TYPES,
            close_loop=False  # Важно для Render.com
        )
    except Exception as e:
        logger.critical(f"Фатальная ошибка: {str(e)}")
    finally:
        logger.info("Бот остановлен")

if __name__ == '__main__':
    main()
