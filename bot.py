import os
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv('TELEGRAM_TOKEN')

DIAGNOSIS_DATA = {
    1: {
        'problems': ['Покраснение', 'Зуд', 'Икота'],
        'parts': ['уха', 'носа', 'пальца'],
        'severity': ['лёгкой формы']
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

async def get_active_members(chat_id, bot):
    members = []
    async for member in bot.get_chat_members(chat_id):
        if not member.user.is_bot and member.user.username:
            members.append(member.user)
    return members

async def generate_diagnosis(level):
    data = DIAGNOSIS_DATA[max(1, min(3, level))]
    return (
        f"{random.choice(data['problems'])} "
        f"{random.choice(data['parts'])} "
        f"{random.choice(data['severity'])}"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👨⚕️ Бот-диагност для групп\n\n"
        "Добавьте меня в группу как администратора и используйте:\n"
        "/diagnose [1-3] - поставить диагноз случайному участнику\n"
        "Пример: /diagnose 3"
    )

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ['group', 'supergroup']:
        return
    
    try:
        members = await get_active_members(update.effective_chat.id, context.bot)
        if not members:
            await update.message.reply_text("😕 В чате нет подходящих участников")
            return

        user = random.choice(members)
        level = int(context.args[0]) if context.args else 2
        diagnosis = await generate_diagnosis(level)

        await update.message.reply_text(
            f"🔍 Диагноз для @{user.username}:\n"
            f"{diagnosis.capitalize()}!"
        )
        
    except Exception:
        await update.message.reply_text("⚠️ Ошибка. Проверьте:\n"
                                      "1. Я администратор\n"
                                      "2. В чате есть участники")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("diagnose", diagnose))
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Необходим TELEGRAM_TOKEN!")
        exit(1)
    main()
