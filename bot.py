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

TOKEN = os.getenv('TELEGRAM_TOKEN')

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

async def get_chat_members_safe(bot, chat_id):
    """Безопасное получение участников чата с логами"""
    try:
        logger.info(f"Попытка получить участников чата {chat_id}")
        members = []
        async for member in bot.get_chat_members(chat_id):
            if not member.user.is_bot:
                members.append(member.user)
                logger.info(f"Найден пользователь: {member.user.full_name} (ID: {member.user.id})")
        logger.info(f"Всего найдено участников: {len(members)}")
        return members
    except Exception as e:
        logger.error(f"Ошибка при получении участников: {str(e)}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start с проверкой прав"""
    try:
        user = update.effective_user
        logger.info(f"Команда /start от {user.full_name} (ID: {user.id})")
        
        text = (
            "👨⚕️ Бот-диагност\n\n"
            "Добавьте меня в группу как администратора и используйте:\n"
            "/diagnose [1-3] - поставить диагноз случайному участнику\n"
            "Пример: /diagnose 2"
        )
        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Ошибка в /start: {str(e)}")

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный обработчик команды /diagnose"""
    try:
        chat = update.effective_chat
        user = update.effective_user
        logger.info(f"Запрос диагноза от {user.full_name} в чате {chat.id}")

        # Проверка типа чата
        if chat.type not in ['group', 'supergroup']:
            logger.warning("Команда вызвана не в группе")
            await update.message.reply_text("🚫 Команда работает только в группах!")
            return

        # Получение участников
        members = await get_chat_members_safe(context.bot, chat.id)
        
        if not members:
            logger.warning("Нет подходящих участников")
            await update.message.reply_text("😕 Не найдено активных пользователей")
            return

        # Выбор случайного участника
        target_user = random.choice(members)
        logger.info(f"Выбран пользователь: {target_user.full_name} (ID: {target_user.id})")

        # Определение уровня сложности
        try:
            level = int(context.args[0]) if context.args else 2
            level = max(1, min(3, level))
        except:
            level = 2
            logger.warning("Неверный уровень, установлен по умолчанию 2")

        # Генерация диагноза
        data = DIAGNOSIS_DATA[level]
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        ).capitalize()

        # Формирование ответа
        username = f"@{target_user.username}" if target_user.username else target_user.full_name
        response = f"🔍 Диагноз для {username}:\n{diagnosis}!"
        
        logger.info(f"Отправка диагноза: {response}")
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
        await update.message.reply_text("⚠️ Произошла ошибка, попробуйте позже")

def main():
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Регистрация обработчиков
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("diagnose", diagnose))
        
        logger.info("Бот запущен...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.critical(f"Фатальная ошибка: {str(e)}")
    finally:
        logger.info("Работа бота завершена")

if __name__ == '__main__':
    if not TOKEN:
        logger.error("Требуется переменная окружения TELEGRAM_TOKEN!")
        exit(1)
    main()
