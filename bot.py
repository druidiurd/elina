import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import re
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import json

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфігурація
TELEGRAM_BOT_TOKEN = "8285203127:AAGIvOvSzctyegI3-olZKSqd5KYq55898E8"
ABACUS_API_KEY = "s2_7ef3d5d6f29246498d2c929662499308"
ABACUS_API_URL = "https://api.abacus.ai/chatllm/v1/chat"

# Ініціалізація Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Ініціалізація бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

class ActivityTracker:
    def __init__(self):
        self.activity_types = {
            'meal': ['їм', 'обід', 'сніданок', 'вечеря', 'перекус', 'готую', 'роблю обід'],
            'work': ['робота', 'працюю', 'зустріч', 'мітинг', 'проект', 'завдання'],
            'exercise': ['спорт', 'тренування', 'біг', 'присідання', 'віджимання', 'зал'],
            'rest': ['відпочинок', 'перерва', 'дивлюся', 'читаю', 'слухаю'],
            'cleaning': ['прибирання', 'миття', 'прання', 'порядок'],
            'meeting': ['зустріч з', 'бачився з', 'розмова з'],
            'drink': ['п\'ю', 'випив', 'кава', 'чай', 'вода']
        }

    async def detect_activity_type(self, text: str) -> Dict:
        """Визначає тип активності з тексту"""
        text_lower = text.lower()

        # Простий парсинг за ключовими словами
        for activity_type, keywords in self.activity_types.items():
            for keyword in keywords:
                if keyword in text_lower:
                    details = await self._extract_details(text, activity_type)
                    return {
                        'type': activity_type,
                        'subtype': details.get('subtype', ''),
                        'details': details,
                        'auto_detected': True
                    }

        # Якщо не вдалося визначити - використовуємо AI
        ai_result = await self._analyze_with_ai(text)
        return ai_result

    async def _extract_details(self, text: str, activity_type: str) -> Dict:
        """Витягує деталі залежно від типу активності"""
        details = {'description': text}

        if activity_type == 'meal':
            food_items = await self._extract_food_items(text)
            details['food_items'] = food_items
            details['subtype'] = self._detect_meal_type(text)

        elif activity_type == 'exercise':
            exercise_info = await self._extract_exercise_info(text)
            details.update(exercise_info)

        elif activity_type == 'meeting':
            people = self._extract_people(text)
            details['people'] = people

        elif activity_type == 'drink':
            drink_info = self._extract_drink_info(text)
            details.update(drink_info)

        return details

    async def _extract_food_items(self, text: str) -> List[str]:
        """Витягує продукти з тексту"""
        common_foods = ['курка', 'макарон', 'рис', 'картопля', 'м\'ясо', 'риба', 'овочі']
        found_foods = []

        for food in common_foods:
            if food in text.lower():
                found_foods.append(food)

        return found_foods

    def _detect_meal_type(self, text: str) -> str:
        """Визначає тип прийому їжі"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['сніданок', 'ранок']):
            return 'breakfast'
        elif any(word in text_lower for word in ['обід', 'ланч']):
            return 'lunch'
        elif any(word in text_lower for word in ['вечеря', 'вечір']):
            return 'dinner'
        else:
            return 'snack'

    async def _extract_exercise_info(self, text: str) -> Dict:
        """Витягує інформацію про вправи"""
        numbers = re.findall(r'\d+', text)
        repetitions = int(numbers[0]) if numbers else 0

        exercise_types = {
            'присідання': 'squats',
            'віджимання': 'push-ups',
            'біг': 'running',
            'планка': 'plank'
        }

        exercise_type = 'general'
        for ukr_name, eng_name in exercise_types.items():
            if ukr_name in text.lower():
                exercise_type = eng_name
                break

        return {
            'exercise_type': exercise_type,
            'repetitions': repetitions
        }

    def _extract_people(self, text: str) -> List[str]:
        """Витягує імена людей з тексту"""
        people = []
        if ' з ' in text.lower():
            parts = text.lower().split(' з ')
            if len(parts) > 1:
                person = parts[1].split()[0]
                people.append(person)

        return people

    def _extract_drink_info(self, text: str) -> Dict:
        """Витягує інформацію про напої"""
        drink_types = {
            'вода': 'water',
            'кава': 'coffee',
            'чай': 'tea'
        }

        drink_type = 'water'
        for ukr_name, eng_name in drink_types.items():
            if ukr_name in text.lower():
                drink_type = eng_name
                break

        numbers = re.findall(r'\d+', text)
        amount = int(numbers[0]) if numbers else 1

        return {
            'drink_type': drink_type,
            'amount': amount
        }

    async def _analyze_with_ai(self, text: str) -> Dict:
        """Використовує Abacus ChatLLM API для аналізу складних активностей"""
        try:
            prompt = f"""
            Проаналізуй цю активність користувача і визнач:
            1. Тип активності (meal, work, rest, meeting, cleaning, exercise, drink, other)
            2. Підтип (якщо є)
            3. Деталі активності

            Текст: "{text}"

            Відповідь дай у форматі JSON:
            {{
                "type": "тип_активності",
                "subtype": "підтип",
                "details": {{"description": "опис", "додаткові_поля": "значення"}},
                "auto_detected": false
            }}
            """

            response = requests.post(
                ABACUS_API_URL,
                headers={
                    'Authorization': f'Bearer {{ABACUS_API_KEY}}',
                    'Content-Type': 'application/json'
                },
                json={
                    'messages': [{'role': 'user', 'content': prompt}],
                    'model': 'claude-3-sonnet'
                }
            )

            if response.status_code == 200:
                ai_response = response.json()
                content = ai_response['choices'][0]['message']['content']

                try:
                    result = json.loads(content)
                    return result
                except json.JSONDecodeError:
                    logger.error(f"Не вдалося парсити AI відповідь: {content}")

        except Exception as e:
            logger.error(f"Помилка при виклику AI API: {e}")

        # Fallback
        return {
            'type': 'other',
            'subtype': '',
            'details': {'description': text},
            'auto_detected': False
        }

class UserManager:
    @staticmethod
    async def get_or_create_user(telegram_user: types.User) -> Dict:
        """Отримує або створює користувача в Firestore"""
        user_ref = db.collection('users').document(str(telegram_user.id))
        user_doc = user_ref.get()

        if user_doc.exists:
            return user_doc.to_dict()

        user_data = {
            'telegram_id': str(telegram_user.id),
            'username': telegram_user.username or '',
            'first_name': telegram_user.first_name or '',
            'created_at': datetime.utcnow(),
            'settings': {
                'reminder_interval': 60,
                'timezone': 'Europe/Kiev',
                'daily_summary_time': '23:00',
                'mood_tracking': True,
                'water_goal': 8,
                'language': 'uk'
            },
            'goals': {
                'exercise_per_week': 3,
                'no_sweets_days': 5
            }
        }

        user_ref.set(user_data)
        return user_data

    @staticmethod
    async def save_activity(user_id: str, activity_data: Dict, raw_text: str):
        """Зберігає активність в Firestore"""
        now = datetime.utcnow()

        # Парсимо час з повідомлення
        time_match = re.match(r'^(\d{1,2}):(\d{2})', raw_text.strip())
        if time_match:
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            today = datetime.now().date()
            activity_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
        else:
            activity_time = now

        activity_doc = {
            'user_id': user_id,
            'timestamp': activity_time,
            'date': activity_time.strftime('%Y-%m-%d'),
            'type': activity_data['type'],
            'subtype': activity_data['subtype'],
            'details': activity_data['details'],
            'raw_text': raw_text,
            'mood': '',
            'auto_detected': activity_data['auto_detected'],
            'created_at': now
        }

        db.collection('activities').add(activity_doc)

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
