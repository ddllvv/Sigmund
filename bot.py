import os
import sys
import random
import logging
from pyrogram import Client
from pyrogram.errors import RPCError
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.utils.exceptions import TerminatedByOtherGetUpdates

# Настройка логгирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверка переменных окружения
if not all([API_ID, API_HASH, BOT_TOKEN]):
    logger.critical("❌ Отсутствуют переменные окружения!")
    sys.exit(1)

DIAGNOSIS_DATA = {
    1: {
        "problems": ["Покраснение", "Зуд", "Икота"],
        "parts": ["уха", "носа", "пальца"],
        "severity": ["начальной стадии"]
    },
    2: {
        "problems": ["Паралич", "Гастрит", "Аритмия"],
        "parts": ["ребра", "колена", "селезёнки"],
        "severity": ["средней тяжести"]
    },
    3: {
        "problems": ["Гангрена", "Дегенерация", "Тромбоз"],
        "parts": ["гипоталамуса", "надкостницы", "яичка"],
        "severity": ["терминальной стадии"]
    }
}

# Инициализация клиентов
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
pyro_client = Client(
    "my_pyro_session",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

class ChatManager:
    """Класс для управления участниками чатов"""
    def __init__(self):
        self.members = {}

    def _convert_chat_id(self, chat_id: int) -> int:
        """Корректное преобразование ID чата для Pyrogram"""
        try:
            # Если ID уже в формате супергруппы
            if str(chat_id).startswith("-100"):
                return int(chat_id)
            
            # Если ID группы, но без префикса
            if chat_id < 0:
                return int(f"-100{abs(chat_id)}")
            
            return chat_id
        except Exception as e:
            logger.error(f"Ошибка конвертации ID: {str(e)}")
            return chat_id

    async def update_members(self, chat_id: int):
        """Обновление списка участников"""
        try:
            pyro_chat_id = self._convert_chat_id(chat_id)
            logger.info(f"Original ID: {chat_id} -> Pyro ID: {pyro_chat_id}")

            async with pyro_client:
                members = []
                async for member in pyro_client.get_chat_members(pyro_chat_id):
                    user = member.user
                    if not user.is_bot:
                        members.append(user)
                
                self.members[chat_id] = members
                logger.info(f"Обновлено участников: {len(members)}")

        except RPCError as e:
            error_msg = f"Pyrogram Error: {str(e)}"
            if "CHAT_ID_INVALID" in str(e):
                error_msg += f"\n⚠️ Неверный ID чата: {pyro_chat_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Ошибка: {str(e)}")
            raise

chat_manager = ChatManager()

@dp.errors_handler(exception=TerminatedByOtherGetUpdates)
async def handle_terminated_error(update, error):
    logger.critical("⚠️ Обнаружен конфликт экземпляров! Принудительная остановка...")
    await bot.close()
    await pyro_client.stop()
    sys.exit(1)

def generate_diagnosis(level: int) -> str:
    data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
    return (
        f"{random.choice(data['problems'])} "
        f"{random.choice(data['parts'])} "
        f"{random.choice(data['severity'])}"
    ).capitalize()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    text = (
        "👨⚕️ Бот-диагност\n\n"
        "Команды:\n"
        "/diagnose [уровень] - ваш диагноз\n"
        "/dg @юзер [уровень] - диагноз участнику\n"
        "/rf - обновить список участников\n\n"
        "Уровни: 1-3 (по умолчанию 2)"
    )
    await message.reply(text)

@dp.message_handler(commands=['rf'])
async def refresh(message: types.Message):
    try:
        chat_id = message.chat.id
        logger.info(f"Получен ID чата: {chat_id}")
        
        await chat_manager.update_members(chat_id)
        members = chat_manager.members.get(chat_id, [])
        
        member_list = "\n".join([f"• {m.username or m.first_name}" for m in members])
        await message.reply(f"🔄 Участников: {len(members)}\n{member_list}")
        
    except Exception as e:
        await message.reply(f"❌ Ошибка: {str(e)}")

@dp.message_handler(commands=['diagnose'])
async def self_diagnose(message: types.Message):
    try:
        args = message.get_args().split()
        level = int(args[0]) if args else 2
        level = max(1, min(3, level))
        
        diagnosis = generate_diagnosis(level)
        await message.reply(f"🩺 Ваш диагноз (уровень {level}):\n{diagnosis}!")
    except:
        await message.reply("⚠️ Используйте: /diagnose [1-3]")

@dp.message_handler(commands=['dg'])
async def user_diagnose(message: types.Message):
    try:
        args = message.get_args().split()
        if not args:
            raise ValueError("Укажите @username")
        
        target = args[0].lstrip('@').lower()
        level = int(args[1]) if len(args) > 1 else 2
        level = max(1, min(3, level))
        
        members = chat_manager.members.get(message.chat.id, [])
        user = next((u for u in members if u.username and u.username.lower() == target), None)
        
        if not user:
            raise ValueError(f"Пользователь @{target} не найден")
            
        diagnosis = generate_diagnosis(level)
        await message.reply(
            f"🔍 Диагноз для @{user.username} (уровень {level}):\n"
            f"{diagnosis}!"
        )
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {str(e)}")

async def shutdown():
    await bot.close()
    await pyro_client.stop()

if __name__ == '__main__':
    try:
        executor.start_polling(
            dp,
            skip_updates=True,
            on_shutdown=shutdown,
            timeout=30,
            relax=0.5
        )
    except TerminatedByOtherGetUpdates:
        logger.critical("Обнаружено несколько экземпляров бота!")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"ФАТАЛЬНАЯ ОШИБКА: {str(e)}")
        sys.exit(1)
