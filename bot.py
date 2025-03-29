import os
import random
import logging
import traceback
from pyrogram import Client
from pyrogram.errors import RPCError
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.utils.exceptions import TerminatedByOtherGetUpdates

# Конфигурация логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Данные для диагнозов
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
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

class ChatManager:
    """Управление участниками чатов"""
    def __init__(self):
        self.members = {}
    
    async def update_members(self, chat_id: int):
        """Обновление списка участников с обработкой ошибок"""
        try:
            pyro_chat_id = self._convert_chat_id(chat_id)
            logger.info(f"Обновление чата {chat_id} -> {pyro_chat_id}")

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
            if "CHAT_ADMIN_REQUIRED" in str(e):
                error_msg += "\n❗ Бот должен быть администратором!"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _convert_chat_id(self, chat_id: int) -> int:
        """Конвертация ID для супергрупп"""
        return int(f"-100{abs(chat_id)}") if chat_id < 0 else chat_id

chat_manager = ChatManager()

@dp.errors_handler(exception=TerminatedByOtherGetUpdates)
async def handle_terminated_error(update, error):
    """Обработка конфликта экземпляров"""
    logger.critical("Обнаружено несколько экземпляров бота! Остановка...")
    await bot.close()
    os._exit(1)  # Принудительное завершение

def generate_diagnosis(level: int) -> str:
    """Генерация случайного диагноза"""
    data = DIAGNOSIS_DATA.get(level, DIAGNOSIS_DATA[2])
    return (
        f"{random.choice(data['problems'])} "
        f"{random.choice(data['parts'])} "
        f"{random.choice(data['severity'])}"
    ).capitalize()

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    """Главное меню"""
    text = (
        "👨⚕️ Бот-диагност\n\n"
        "Команды:\n"
        "/diagnose [уровень] - ваш диагноз\n"
        "/dg @юзер [уровень] - диагноз участнику\n"
        "/rf - обновить список участников\n\n"
        "Уровни: 1-3 (по умолчанию 2)\n"
        "Пример: /dg @user 3"
    )
    await message.reply(text)

@dp.message_handler(commands=['rf'])
async def refresh(message: types.Message):
    """Принудительное обновление списка"""
    try:
        chat_id = message.chat.id
        await chat_manager.update_members(chat_id)
        
        members = chat_manager.members.get(chat_id, [])
        member_list = "\n".join([f"• {m.username or m.first_name}" for m in members])
        
        await message.reply(f"🔄 Участников: {len(members)}\n{member_list}")
    except Exception as e:
        logger.error(traceback.format_exc())
        await message.reply(f"❌ Ошибка: {str(e)}")

@dp.message_handler(commands=['diagnose'])
async def self_diagnose(message: types.Message):
    """Диагноз для себя"""
    try:
        args = message.get_args().split()
        level = 2
        
        if args and args[0].isdigit():
            level = max(1, min(3, int(args[0])))
        
        diagnosis = generate_diagnosis(level)
        await message.reply(f"🩺 Ваш диагноз (уровень {level}):\n{diagnosis}!")
    except Exception as e:
        logger.error(traceback.format_exc())
        await message.reply("⚠️ Неверный формат команды")

@dp.message_handler(commands=['dg'])
async def user_diagnose(message: types.Message):
    """Диагноз для участника"""
    try:
        chat_id = message.chat.id
        args = message.get_args().split()
        
        if not args:
            raise ValueError("Укажите @username")
            
        target_username = args[0].lstrip('@').lower()
        level = 2
        
        if len(args) > 1 and args[1].isdigit():
            level = max(1, min(3, int(args[1])))
        
        members = chat_manager.members.get(chat_id, [])
        user = next(
            (u for u in members if u.username and u.username.lower() == target_username),
            None
        )
        
        if not user:
            raise ValueError("Пользователь не найден")
            
        diagnosis = generate_diagnosis(level)
        await message.reply(
            f"🔍 Диагноз для @{user.username} (уровень {level}):\n"
            f"{diagnosis}!"
        )
    except Exception as e:
        logger.error(traceback.format_exc())
        await message.reply(f"⚠️ Ошибка: {str(e)}")

async def on_shutdown(dp):
    """Действия при завершении работы"""
    await bot.close()

if __name__ == '__main__':
    try:
        executor.start_polling(
            dp,
            skip_updates=True,
            on_shutdown=on_shutdown,
            timeout=30,
            relax=0.5
        )
    except Exception as e:
        logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА: {traceback.format_exc()}")
