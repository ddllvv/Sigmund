import os
import random
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import BadRequest, Forbidden

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
    """Безопасное получение участников чата с обработкой ошибок"""
    try:
        members = []
        async for member in bot.get_chat_members(chat_id):
            user = member.user
            if not user.is_bot:
                members.append(user)
                logger.debug(f"Найден пользователь: {user.full_name} (ID: {user.id}, @{user.username})")
        return members
    except Forbidden as e:
        logger.error(f"Ошибка доступа: {e.message}")
        return None
    except Exception as e:
        logger.error(f"Ошибка получения участников: {str(e)}")
        return []

async def generate_diagnosis(level: int) -> str:
    """Генерирует диагноз для указанного уровня"""
    level = max(1, min(3, level))
    data = DIAGNOSIS_DATA[level]
    return (
        f"{random.choice(data['problems'])} "
        f"{random.choice(data['parts'])} "
        f"{random.choice(data['severity'])}"
    ).capitalize()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    help_text = (
        "👨⚕️ Бот-диагност для групп\n\n"
        "Команды:\n"
        "/diagnose [@юзер] [уровень 1-3] - поставить диагноз\n"
        "/check_rights - проверить права бота\n\n"
        "Примеры:\n"
        "/diagnose 2 - случайному участнику\n"
        "/diagnose @username 3 - конкретному пользователю"
    )
    await update.message.reply_text(help_text)

async def check_rights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка прав бота в чате"""
    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=context.bot.id
        )
        
        rights_info = (
            f"Статус: {chat_member.status}\n"
            f"Может управлять чатом: {chat_member.can_manage_chat}\n"
            f"Видит участников: {chat_member.can_manage_chat}\n"
            f"Может читать сообщения: {chat_member.can_read_all_messages}"
        )
        
        await update.message.reply_text(f"Права бота:\n{rights_info}")
        
    except Exception as e:
        logger.error(f"Ошибка проверки прав: {str(e)}")
        await update.message.reply_text("❌ Ошибка проверки прав")

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Улучшенный обработчик команды /diagnose"""
    try:
        chat = update.effective_chat
        args = context.args
        
        logger.info(f"Получена команда от {update.effective_user.id} в чате {chat.id}")
        
        # Проверка типа чата
        if chat.type not in ['group', 'supergroup']:
            await update.message.reply_text("🚫 Команда работает только в группах!")
            return

        # Получение участников
        members = await get_chat_members_safe(context.bot, chat.id)
        
        if members is None:
            await update.message.reply_text("🔒 У бота нет прав для просмотра участников!")
            return
            
        if not members:
            await update.message.reply_text("😢 В чате нет доступных участников")
            return

        # Парсинг аргументов
        target_user = None
        level = 2
        
        if args:
            # Поиск упоминания пользователя
            for i, arg in enumerate(args):
                if arg.startswith('@'):
                    username = arg[1:].lower()
                    target_user = next((u for u in members if u.username and u.username.lower() == username), None)
                    if target_user:
                        # Обработка уровня после упоминания
                        if len(args) > i+1:
                            try: level = int(args[i+1])
                            except: pass
                        break
            # Если не нашли упоминание - проверяем первый аргумент как уровень
            if not target_user:
                try: level = int(args[0])
                except: pass

        # Выбор случайного пользователя, если не указан
        if not target_user:
            target_user = random.choice(members)
            logger.info(f"Выбран случайный пользователь: {target_user.id}")

        # Проверка уровня
        level = max(1, min(3, level))
        
        # Генерация диагноза
        diagnosis = await generate_diagnosis(level)

        # Формирование ответа
        username = f"@{target_user.username}" if target_user.username else target_user.full_name
        response = (
            f"🔍 Диагноз для {username} (уровень {level}):\n"
            f"{diagnosis}!"
        )
        
        await update.message.reply_text(response)

    except BadRequest as e:
        logger.error(f"Ошибка API: {str(e)}")
        await update.message.reply_text("⚠️ Ошибка обработки запроса")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ Произошла внутренняя ошибка")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check_rights", check_rights))
    application.add_handler(CommandHandler("diagnose", diagnose))
    
    logger.info("Бот запущен...")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        close_loop=False
    )

if __name__ == '__main__':
    if not TOKEN:
        logger.error("❌ Требуется переменная окружения TELEGRAM_TOKEN!")
        exit(1)
    main()
