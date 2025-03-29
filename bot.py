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
        "problems": [
            "Лёгкое покраснение", "Сезонный зуд", "Икота", "Насморк", 
            "Чихание", "Головокружение", "Легкая изжога", "Сонливость",
            "Метеоризм", "Икота", "Легкая сыпь", "Слезотечение",
            "Заложенность", "Легкий кашель", "Укачивание",
            "Легкая аллергия", "Судорога", "Шелушение"
        ],
        "parts": [
            "уха", "носа", "мизинца", "века", "коленной чашечки",
            "локтя", "пятки", "брови", "языка", "пупка",
            "указательного пальца", "мозоли", "щеки", "подбородка",
            "переносицы", "ногтя", "запястья", "виска", "гортани",
            "лимфатического узла"
        ],
        "severity": [
            "начальной стадии", "лёгкой формы", "эпизодического характера",
            "сезонного обострения", "после употребления острой пищи",
            "при контакте с кошками", "во время цветения амброзии",
            "после стрессовых ситуаций", "при смене погоды",
            "после долгого сидения"
        ]
    },
    2: {
        "problems": [
            "Гастрит", "Бронхит", "Гипертония", "Аритмия", "Панкреатит",
            "Отит", "Цистит", "Конъюнктивит", "Синусит", "Артрит",
            "Экзема", "Геморрой", "Тонзиллит", "Невралгия", "Мигрень",
            "Пиелонефрит", "Холецистит", "Колит", "Фарингит", "Пульпит"
        ],
        "parts": [
            "надпочечников", "лимфатической системы", "печени",
            "поджелудочной железы", "поясничного отдела", "грудной клетки",
            "голосовых связок", "селезёнки", "желчного пузыря",
            "двенадцатиперстной кишки", "тазобедренного сустава",
            "среднего уха", "корня зуба", "шейных позвонков",
            "плечевого нерва", "лимфоузлов", "надколенника",
            "мениска", "ахиллова сухожилия", "предплечья"
        ],
        "severity": [
            "средней тяжести", "хронической формы", "с рецидивами",
            "с риском осложнений", "требующее стационара",
            "с температурой 38-39°C", "с ограничением подвижности",
            "с воспалительным процессом", "с образованием эрозий",
            "с риском перехода в хроническую форму"
        ]
    },
    3: {
        "problems": [
            "Инфаркт миокарда", "Инсульт", "Онкология", "Сепсис",
            "Тромбоэмболия", "Перитонит", "Менингит", "Гангрена",
            "Почечная недостаточность", "Цирроз печени",
            "Лейкемия", "Энцефалит", "Туберкулёз", "СПИД",
            "Болезнь Крона", "Рассеянный склероз", "Боковой амиотрофический склероз",
            "Муковисцидоз", "Тяжёлый острый панкреатит", "Кардиогенный шок"
        ],
        "parts": [
            "коронарных артерий", "ствола головного мозга",
            "спинного мозга", "лёгочной артерии", "брюшной аорты",
            "костного мозга", "мозжечка", "перикарда", 
            "поджелудочной железы (некроз)", "почечных клубочков",
            "лимфатической системы (метастазы)", "гипофиза",
            "межпозвоночных дисков (абсцесс)", "печени (цирроз)",
            "лёгких (фиброз)", "селезёнки (разрыв)",
            "надпочечников (кровоизлияние)", "щитовидной железы (анаплазия)",
            "мозговых оболочек", "сердечных клапанов"
        ],
        "severity": [
            "терминальной стадии", "с метастазированием",
            "с полиорганной недостаточностью", "несовместимое с жизнью",
            "требующее реанимации", "с летальностью 90%",
            "с перфорацией органов", "с генерализованным сепсисом",
            "с тотальным некрозом тканей", "с отказом всех систем"
        ]
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
            if str(chat_id).startswith("-100"):
                return int(chat_id)
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
        "/random_dg [уровень] - случайному участнику\n"
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
            f"🔍 Диагноз для @{user.username}:\n"
            f"{diagnosis}!"
        )
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {str(e)}")

@dp.message_handler(commands=['random_dg'])
async def random_diagnose(message: types.Message):
    """Диагноз случайному участнику"""
    try:
        chat_id = message.chat.id
        args = message.get_args().split()
        
        # Получаем уровень
        level = int(args[0]) if args and args[0].isdigit() else 2
        level = max(1, min(3, level))
        
        # Получаем участников
        members = chat_manager.members.get(chat_id, [])
        if not members:
            await message.reply("❌ Нет данных об участниках. Используйте /rf")
            return
            
        # Выбираем случайного участника
        random_user = random.choice(members)
        username = random_user.username or random_user.first_name
        
        # Генерируем диагноз
        diagnosis = generate_diagnosis(level)
        await message.reply(
            f"У @{username} {diagnosis}!"
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
