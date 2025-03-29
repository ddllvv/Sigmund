import os
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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

async def get_members(chat_id, bot):
    members = []
    try:
        async for member in bot.get_chat_members(chat_id):
            if not member.user.is_bot:
                members.append(member.user)
    except Exception as e:
        print(f"Ошибка получения участников: {e}")
    return members

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🩺 Бот-диагност для групп\n"
        "Используйте /diagnose [1-3]\n"
        "Пример: /diagnose 3"
    )

async def diagnose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        if chat.type not in ['group', 'supergroup']:
            return

        members = await get_members(chat.id, context.bot)
        if not members:
            await update.message.reply_text("😢 Нет доступных участников")
            return

        user = random.choice(members)
        username = user.username or user.first_name
        level = int(context.args[0]) if context.args else 2
        level = max(1, min(3, level))

        data = DIAGNOSIS_DATA[level]
        diagnosis = (
            f"{random.choice(data['problems'])} "
            f"{random.choice(data['parts'])} "
            f"{random.choice(data['severity'])}"
        )

        await update.message.reply_text(
            f"🔍 Диагноз для @{username}:\n"
            f"{diagnosis.capitalize()}!"
        )

    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Ошибка выполнения команды")

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("diagnose", diagnose))
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Требуется TELEGRAM_TOKEN!")
        exit(1)
    main()
