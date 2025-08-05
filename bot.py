import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import firebase_admin
from firebase_admin import credentials, firestore

# Імпорти конфігурації
from config import TELEGRAM_BOT_TOKEN, FIREBASE_KEY_PATH

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ініціалізація Firebase
cred = credentials.Certificate(FIREBASE_KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# Імпорти модулів (після ініціалізації Firebase)
from modules.activity_tracker import ActivityTracker
from modules.user_manager import UserManager, init_db

# Ініціалізуємо базу даних для модулів
init_db(db)

# Ініціалізація бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Ініціалізація трекера
tracker = ActivityTracker()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    user = await UserManager.get_or_create_user(message.from_user)

    welcome_text = f"""
🤖 Привіт, {user['first_name']}!

Я твій особистий асистент для відстеження активностей.

Просто пиши мені, що ти робиш, наприклад:
• "12:45 роблю обід, курку і макарон"
• "14:00 почав роботу над проектом"
• "15:30 зробив 20 присідань"

Команди:
/help - допомога
/summary - підсумок дня
/stats - статистика
/settings - налаштування
    """

    await message.answer(welcome_text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = """
📋 **Доступні команди:**

/start - почати роботу з ботом
/summary - підсумок дня/тижня
/stats - детальна статистика
/diet - аналіз раціону
/exercise - аналіз фізичних вправ
/settings - налаштування бота
/help - ця довідка

**Як користуватися:**
Просто пиши свої активності у вільній формі!
    """

    await message.answer(help_text, parse_mode="Markdown")

@dp.message()
async def handle_activity(message: Message):
    """Обробка звичайних повідомлень як активностей"""
    try:
        user = await UserManager.get_or_create_user(message.from_user)
        activity_data = await tracker.detect_activity_type(message.text)

        await UserManager.save_activity(
            str(message.from_user.id),
            activity_data,
            message.text
        )

        response = f"✅ Записав: {activity_data['type']}"
        if activity_data['subtype']:
            response += f" ({activity_data['subtype']})"

        if activity_data['type'] == 'meal' and activity_data['details'].get('food_items'):
            foods = ', '.join(activity_data['details']['food_items'])
            response += f"\n🍽 Продукти: {foods}"

        elif activity_data['type'] == 'exercise':
            if activity_data['details'].get('repetitions'):
                response += f"\n💪 {activity_data['details']['repetitions']} повторень"

        elif activity_data['type'] == 'drink':
            drink_type = activity_data['details'].get('drink_type', 'напій')
            amount = activity_data['details'].get('amount', 1)
            response += f"\n🥤 {amount} {drink_type}"

        await message.answer(response)

    except Exception as e:
        logger.error(f"Помилка при обробці активності: {e}")
        await message.answer("❌ Виникла помилка при збереженні активності. Спробуй ще раз.")

async def main():
    """Запуск бота"""
    logger.info("Запускаю бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())