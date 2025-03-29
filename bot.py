import os
import random
import logging
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

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

async def get_chat_members(client, chat_id):
    """Получение участников чата"""
    try:
        participants = await client(GetParticipantsRequest(
            channel=chat_id,
            filter=ChannelParticipantsRecent(),
            offset=0,
            limit=100,
            hash=0
        ))
        return [user for user in participants.users if not user.bot]
    except Exception as e:
        logger.error(f"Ошибка получения участников: {str(e)}")
        return []

async def generate_diagnosis(level):
    """Генерация диагноза"""
    level = max(1, min(3, level))
    data = DIAGNOSIS_DATA[level]
    return (
        f"{random.choice(data['problems'])} "
        f"{random.choice(data['parts'])} "
        f"{random.choice(data['severity'])}"
    )

async def send_diagnosis(event, level, target_user=None):
    """Отправка диагноза"""
    try:
        chat = await event.get_chat()
        members = await get_chat_members(event.client, chat.id)
        
        if not members:
            await event.reply("😢 В чате нет участников для диагностики")
            return
            
        user = target_user or random.choice(members)
        username = user.username or user.first_name
        diagnosis = await generate_diagnosis(level)
        
        await event.reply(
            f"🔍 Диагноз для @{username} (уровень {level}):\n"
            f"{diagnosis}!"
        )
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await event.reply("⚠️ Произошла ошибка")

# Инициализация клиента
client = TelegramClient('diagnosis_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Обработчик команды /start"""
    help_text = (
        "👨⚕️ Бот-диагност для групп\n\n"
        "Команды:\n"
        "/diagnose [@юзер] [уровень 1-3]\n"
        "Примеры:\n"
        "/diagnose 2 - случайному участнику\n"
        "/diagnose @username 3"
    )
    await event.reply(help_text)

@client.on(events.NewMessage(pattern='/diagnose'))
async def diagnose_handler(event):
    """Обработчик команды /diagnose"""
    try:
        args = event.text.split()[1:]
        level = 2
        target_user = None
        
        # Парсинг аргументов
        for arg in args:
            if arg.startswith('@'):
                target_user = next((u for u in await get_chat_members(event.client, event.chat_id) 
                                  if u.username == arg[1:]), None)
            elif arg.isdigit():
                level = int(arg)
        
        await send_diagnosis(event, level, target_user)
        
    except Exception as e:
        logger.error(f"Ошибка обработки команды: {str(e)}")
        await event.reply("❌ Некорректная команда")

if __name__ == '__main__':
    logger.info("Бот запущен...")
    client.run_until_disconnected()
