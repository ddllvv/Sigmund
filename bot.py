import os
import random
import logging
from pyrogram import Client, filters
from pyrogram.errors import RPCError
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
pyro_client = Client(
    "my_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

class ChatManager:
    def __init__(self):
        self.members = {}
    
    async def update_members(self, chat_id: int):
        try:
            async with pyro_client:
                members = []
                async for member in pyro_client.get_chat_members(chat_id):
                    if not member.user.is_bot:
                        members.append(member.user)
                self.members[chat_id] = members
                logger.info(f"Обновлено участников: {len(members)}")
        except RPCError as e:
            logger.error(f"Pyrogram error: {str(e)}")

chat_manager = ChatManager()

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
        "Уровни: 1-3 (по умолчанию 2)\n"
        "Пример: /dg @user 3"
    )
    await message.reply(text)

@dp.message_handler(commands=['rf'])
async def refresh(message: types.Message):
    try:
        chat_id = message.chat.id
        await chat_manager.update_members(chat_id)
        members = chat_manager.members.get(chat_id, [])
        
        member_list = "\n".join([f"• {m.username or m.first_name}" for m in members])
        await message.reply(f"🔄 Участников: {len(members)}\n{member_list}")
        
    except Exception as e:
        logger.error(str(e))
        await message.reply("❌ Ошибка обновления")

@dp.message_handler(commands=['diagnose'])
async def self_diagnose(message: types.Message):
    try:
        args = message.get_args().split()
        level = 2
        
        if args and args[0].isdigit() and 1 <= int(args[0]) <= 3:
            level = int(args[0])
            
        diagnosis = generate_diagnosis(level)
        await message.reply(f"🩺 Ваш диагноз (уровень {level}):\n{diagnosis}!")
        
    except Exception as e:
        logger.error(str(e))
        await message.reply("⚠️ Ошибка выполнения")

@dp.message_handler(commands=['dg'])
async def user_diagnose(message: types.Message):
    try:
        chat_id = message.chat.id
        args = message.get_args().split()
        
        if not args:
            await message.reply("❌ Укажите @username")
            return
            
        target_username = args[0].lstrip('@')
        level = 2
        
        if len(args) > 1 and args[1].isdigit() and 1 <= int(args[1]) <= 3:
            level = int(args[1])
            
        members = chat_manager.members.get(chat_id, [])
        user = next((u for u in members if u.username == target_username), None)
        
        if not user:
            await message.reply("❌ Пользователь не найден")
            return
            
        diagnosis = generate_diagnosis(level)
        await message.reply(
            f"🔍 Диагноз для @{target_username} (уровень {level}):\n"
            f"{diagnosis}!"
        )
        
    except Exception as e:
        logger.error(str(e))
        await message.reply("⚠️ Ошибка выполнения")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
