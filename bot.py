import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import re
from typing import Dict, List, Optional
import csv
import io

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InputFile
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import json
import random

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
from config import Config

# Конфігурація
TELEGRAM_BOT_TOKEN = Config.TELEGRAM_BOT_TOKEN
ABACUS_API_KEY = Config.ABACUS_API_KEY
ABACUS_API_URL = Config.ABACUS_API_URL

# Ініціалізація Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Ініціалізація бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# --- Мікро-челленджі ---
CHALLENGES = [
    "Зроби 10 присідань!",
    "Випий склянку води.",
    "Зроби 5-хвилинну перерву для розтяжки.",
    "Пройдися кімнатою.",
    "Напиши 3 речі, за які ти вдячний сьогодні.",
    "Виконай 10 віджимань.",
    "Зроби 10 глибоких вдихів.",
    "Поглянь у вікно і відпочинь очима 1 хвилину."
]

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
                    'Authorization': f'Bearer {ABACUS_API_KEY}',
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

class AnalyticsManager:
    """Модуль аналітики для підсумків та статистики"""
    
    @staticmethod
    async def get_daily_summary(user_id: str, date: str = None) -> str:
        """Генерує підсумок дня"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        activities = db.collection('activities').where('user_id', '==', user_id).where('date', '==', date).stream()
        
        activity_counts = {}
        total_activities = 0
        
        for activity in activities:
            data = activity.to_dict()
            activity_type = data['type']
            activity_counts[activity_type] = activity_counts.get(activity_type, 0) + 1
            total_activities += 1
        
        if total_activities == 0:
            return f"📅 Підсумок за {date}:\nНемає записаних активностей."
        
        summary = f"📅 Підсумок за {date}:\n"
        summary += f"📊 Всього активностей: {total_activities}\n\n"
        
        for activity_type, count in activity_counts.items():
            emoji = {'meal': '🍽', 'work': '💼', 'exercise': '💪', 'rest': '😴', 'drink': '🥤'}.get(activity_type, '📝')
            summary += f"{emoji} {activity_type}: {count}\n"
        
        return summary

    @staticmethod
    async def get_weekly_summary(user_id: str) -> str:
        """Генерує підсумок тижня"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        activities = db.collection('activities').where('user_id', '==', user_id).where('timestamp', '>=', start_date).where('timestamp', '<=', end_date).stream()
        
        daily_counts = {}
        activity_totals = {}
        
        for activity in activities:
            data = activity.to_dict()
            date = data['date']
            activity_type = data['type']
            
            if date not in daily_counts:
                daily_counts[date] = 0
            daily_counts[date] += 1
            
            activity_totals[activity_type] = activity_totals.get(activity_type, 0) + 1
        
        summary = f"📊 Підсумок тижня ({start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')}):\n\n"
        
        if not daily_counts:
            return summary + "Немає записаних активностей за тиждень."
        
        # Найактивніший день
        most_active_day = max(daily_counts, key=daily_counts.get)
        summary += f"🔥 Найактивніший день: {most_active_day} ({daily_counts[most_active_day]} активностей)\n\n"
        
        # Топ активностей
        summary += "🏆 Топ активностей:\n"
        for activity_type, count in sorted(activity_totals.items(), key=lambda x: x[1], reverse=True)[:5]:
            emoji = {'meal': '🍽', 'work': '💼', 'exercise': '💪', 'rest': '😴', 'drink': '🥤'}.get(activity_type, '📝')
            summary += f"{emoji} {activity_type}: {count}\n"
        
        return summary

    @staticmethod
    async def get_diet_analysis(user_id: str, days: int = 7) -> str:
        """Аналіз раціону за останні дні"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        activities = db.collection('activities').where('user_id', '==', user_id).where('type', '==', 'meal').where('timestamp', '>=', start_date).stream()
        
        meal_types = {}
        food_items = {}
        total_meals = 0
        
        for activity in activities:
            data = activity.to_dict()
            subtype = data.get('subtype', 'unknown')
            meal_types[subtype] = meal_types.get(subtype, 0) + 1
            total_meals += 1
            
            # Аналіз продуктів
            details = data.get('details', {})
            if 'food_items' in details:
                for food in details['food_items']:
                    food_items[food] = food_items.get(food, 0) + 1
        
        if total_meals == 0:
            return f"🍽 Аналіз раціону за {days} днів:\nНемає записів про їжу."
        
        analysis = f"🍽 Аналіз раціону за {days} днів:\n"
        analysis += f"📊 Всього прийомів їжі: {total_meals}\n\n"
        
        # Розподіл по типах прийомів їжі
        analysis += "🕐 Розподіл по часу:\n"
        for meal_type, count in meal_types.items():
            emoji = {'breakfast': '🌅', 'lunch': '☀️', 'dinner': '🌙', 'snack': '🍪'}.get(meal_type, '🍽')
            analysis += f"{emoji} {meal_type}: {count}\n"
        
        # Топ продуктів
        if food_items:
            analysis += "\n🥗 Найчастіші продукти:\n"
            for food, count in sorted(food_items.items(), key=lambda x: x[1], reverse=True)[:5]:
                analysis += f"• {food}: {count} разів\n"
        
        return analysis

    @staticmethod
    async def get_exercise_analysis(user_id: str, days: int = 7) -> str:
        """Аналіз фізичних вправ"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        activities = db.collection('activities').where('user_id', '==', user_id).where('type', '==', 'exercise').where('timestamp', '>=', start_date).stream()
        
        exercise_types = {}
        total_repetitions = 0
        total_sessions = 0
        
        for activity in activities:
            data = activity.to_dict()
            details = data.get('details', {})
            exercise_type = details.get('exercise_type', 'general')
            repetitions = details.get('repetitions', 0)
            
            exercise_types[exercise_type] = exercise_types.get(exercise_type, 0) + 1
            total_repetitions += repetitions
            total_sessions += 1
        
        if total_sessions == 0:
            return f"💪 Аналіз вправ за {days} днів:\nНемає записів про фізичні вправи."
        
        analysis = f"💪 Аналіз вправ за {days} днів:\n"
        analysis += f"🏃‍♂️ Всього тренувань: {total_sessions}\n"
        analysis += f"🔢 Всього повторень: {total_repetitions}\n\n"
        
        # Топ вправ
        analysis += "🏆 Найпопулярніші вправи:\n"
        for exercise, count in sorted(exercise_types.items(), key=lambda x: x[1], reverse=True):
            analysis += f"• {exercise}: {count} разів\n"
        
        return analysis

class MoodTracker:
    """Трекер настрою"""
    
    @staticmethod
    async def save_mood(user_id: str, mood: str, note: str = ""):
        """Зберігає настрій користувача"""
        mood_doc = {
            'user_id': user_id,
            'mood': mood,
            'note': note,
            'timestamp': datetime.utcnow(),
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        
        db.collection('moods').add(mood_doc)

    @staticmethod
    async def get_mood_stats(user_id: str, days: int = 7) -> str:
        """Статистика настрою за період"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        moods = db.collection('moods').where('user_id', '==', user_id).where('timestamp', '>=', start_date).stream()
        
        mood_counts = {}
        total_entries = 0
        
        for mood_entry in moods:
            data = mood_entry.to_dict()
            mood = data['mood']
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
            total_entries += 1
        
        if total_entries == 0:
            return f"😊 Статистика настрою за {days} днів:\nНемає записів про настрій."
        
        stats = f"😊 Статистика настрою за {days} днів:\n"
        stats += f"📊 Всього записів: {total_entries}\n\n"
        
        for mood, count in sorted(mood_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_entries) * 100
            emoji = {'відмінно': '😄', 'добре': '😊', 'нормально': '😐', 'погано': '😔', 'жахливо': '😢'}.get(mood, '😊')
            stats += f"{emoji} {mood}: {count} ({percentage:.1f}%)\n"
        
        return stats

class WaterTracker:
    """Трекер води та напоїв"""
    
    @staticmethod
    async def get_water_stats(user_id: str, date: str = None) -> str:
        """Статистика споживання води за день"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        activities = db.collection('activities').where('user_id', '==', user_id).where('type', '==', 'drink').where('date', '==', date).stream()
        
        drink_totals = {'water': 0, 'coffee': 0, 'tea': 0}
        
        for activity in activities:
            data = activity.to_dict()
            details = data.get('details', {})
            drink_type = details.get('drink_type', 'water')
            amount = details.get('amount', 1)
            
            if drink_type in drink_totals:
                drink_totals[drink_type] += amount
        
        stats = f"🥤 Споживання напоїв за {date}:\n"
        stats += f"💧 Вода: {drink_totals['water']} склянок\n"
        stats += f"☕ Кава: {drink_totals['coffee']} чашок\n"
        stats += f"🍵 Чай: {drink_totals['tea']} чашок\n"
        
        # Рекомендації
        if drink_totals['water'] < 8:
            stats += f"\n💡 Рекомендація: випий ще {8 - drink_totals['water']} склянок води!"
        
        return stats

class GoalsManager:
    """Менеджер цілей"""
    
    @staticmethod
    async def check_goals(user_id: str) -> str:
        """Перевіряє прогрес по цілях"""
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return "❌ Користувач не знайдений."
        
        user_data = user_doc.to_dict()
        goals = user_data.get('goals', {})
        
        if not goals:
            return "🎯 У тебе поки немає встановлених цілей.\nВикористай /settings для налаштування."
        
        # Перевірка цілі по спорту за тиждень
        exercise_goal = goals.get('exercise_per_week', 0)
        if exercise_goal > 0:
            # Підрахунок тренувань за тиждень
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            exercises = db.collection('activities').where('user_id', '==', user_id).where('type', '==', 'exercise').where('timestamp', '>=', start_date).stream()
            exercise_count = len(list(exercises))
            
            progress = f"🏃‍♂️ Спорт: {exercise_count}/{exercise_goal} тренувань за тиждень"
            if exercise_count >= exercise_goal:
                progress += " ✅"
            else:
                progress += f" (залишилось: {exercise_goal - exercise_count})"
        
        return f"🎯 Прогрес по цілях:\n{progress}"

class ExportManager:
    """Менеджер експорту даних"""
    
    @staticmethod
    async def export_activities_csv(user_id: str, days: int = 30) -> io.StringIO:
        """Експортує активності у CSV"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        activities = db.collection('activities').where('user_id', '==', user_id).where('timestamp', '>=', start_date).stream()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow(['Дата', 'Час', 'Тип', 'Підтип', 'Опис', 'Деталі'])
        
        for activity in activities:
            data = activity.to_dict()
            timestamp = data.get('timestamp', datetime.now())
            writer.writerow([
                timestamp.strftime('%Y-%m-%d'),
                timestamp.strftime('%H:%M'),
                data.get('type', ''),
                data.get('subtype', ''),
                data.get('raw_text', ''),
                str(data.get('details', {}))
            ])
        
        output.seek(0)
        return output

class ReminderManager:
    """Менеджер нагадувань"""
    
    @staticmethod
    async def check_inactivity(user_id: str) -> bool:
        """Перевіряє, чи був користувач неактивний останню годину"""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        recent_activities = db.collection('activities').where('user_id', '==', user_id).where('timestamp', '>=', one_hour_ago).limit(1).stream()
        
        return len(list(recent_activities)) == 0

    @staticmethod
    async def should_ask_mood(user_id: str) -> bool:
        """Перевіряє, чи треба запитати про настрій"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        mood_today = db.collection('moods').where('user_id', '==', user_id).where('date', '==', today).limit(1).stream()
        
        return len(list(mood_today)) == 0

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

# === КОМАНДИ БОТА ===

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

📋 **Основні команди:**
/help - повна довідка
/summary - підсумок дня/тижня
/diet - аналіз раціону
/exercise - аналіз фізичних вправ
/mood - трекер настрою
/water - статистика напоїв
/goals - прогрес по цілях
/challenge - мікро-челлендж
/export - експорт даних
/settings - налаштування
    """

    await message.answer(welcome_text)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = """
📋 **Доступні команди:**

**Основні:**
/start - почати роботу з ботом
/help - ця довідка

**Аналітика:**
/summary - підсумок дня/тижня
/stats - детальна статистика
/diet - аналіз раціону
/exercise - аналіз фізичних вправ

**Трекінг:**
/mood - записати настрій
/water - статистика напоїв
/goals - прогрес по цілях

**Додаткові:**
/challenge - отримати мікро-челлендж
/export - експорт активностей у CSV
/groupstats - групова статистика
/settings - налаштування бота

**Як користуватися:**
Просто пиши свої активності у вільній формі!
Бот автоматично розпізнає тип активності та збереже деталі.
    """

    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("summary"))
async def cmd_summary(message: Message):
    """Команда /summary - підсумок дня/тижня"""
    user_id = str(message.from_user.id)
    
    # Підсумок дня
    daily_summary = await AnalyticsManager.get_daily_summary(user_id)
    
    # Підсумок тижня
    weekly_summary = await AnalyticsManager.get_weekly_summary(user_id)
    
    full_summary = f"{daily_summary}\n\n{weekly_summary}"
    
    await message.answer(full_summary)

@dp.message(Command("diet"))
async def cmd_diet(message: Message):
    """Команда /diet - аналіз раціону"""
    user_id = str(message.from_user.id)
    
    diet_analysis = await AnalyticsManager.get_diet_analysis(user_id, days=7)
    
    await message.answer(diet_analysis)

@dp.message(Command("exercise"))
async def cmd_exercise(message: Message):
    """Команда /exercise - аналіз фізичних вправ"""
    user_id = str(message.from_user.id)
    
    exercise_analysis = await AnalyticsManager.get_exercise_analysis(user_id, days=7)
    
    await message.answer(exercise_analysis)

@dp.message(Command("mood"))
async def cmd_mood(message: Message):
    """Команда /mood - трекер настрою"""
    await message.answer(
        "😊 Як твій настрій сьогодні?\n\n"
        "Відповідь у форматі: /mood [настрій] [примітка]\n"
        "Наприклад: /mood добре працював продуктивно\n\n"
        "Варіанти настрою: відмінно, добре, нормально, погано, жахливо"
    )

@dp.message(Command("water"))
async def cmd_water(message: Message):
    """Команда /water - статистика напоїв"""
    user_id = str(message.from_user.id)
    
    water_stats = await WaterTracker.get_water_stats(user_id)
    
    await message.answer(water_stats)

@dp.message(Command("goals"))
async def cmd_goals(message: Message):
    """Команда /goals - прогрес по цілях"""
    user_id = str(message.from_user.id)
    
    goals_progress = await GoalsManager.check_goals(user_id)
    
    await message.answer(goals_progress)

@dp.message(Command("challenge"))
async def cmd_challenge(message: Message):
    """Команда /challenge - мікро-челлендж"""
    challenge = random.choice(CHALLENGES)
    
    await message.answer(f"🎯 **Мікро-челлендж для тебе:**\n\n{challenge}\n\nГотовий прийняти виклик? 💪")

@dp.message(Command("export"))
async def cmd_export(message: Message):
    """Команда /export - експорт активностей у CSV"""
    user_id = str(message.from_user.id)
    
    try:
        csv_data = await ExportManager.export_activities_csv(user_id, days=30)
        
        # Створюємо файл для відправки
        csv_content = csv_data.getvalue()
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = f"activities_{datetime.now().strftime('%Y%m%d')}.csv"
        
        await message.answer_document(
            InputFile(csv_file, filename=csv_file.name),
            caption="📊 Твої активності за останні 30 днів у форматі CSV"
        )
        
    except Exception as e:
        logger.error(f"Помилка при експорті: {e}")
        await message.answer("❌ Виникла помилка при експорті даних. Спробуй пізніше.")

@dp.message(Command("groupstats"))
async def cmd_groupstats(message: Message):
    """Команда /groupstats - групова статистика (базова реалізація)"""
    # Базова реалізація - показує загальну кількість користувачів
    users_count = len(list(db.collection('users').stream()))
    
    stats = f"👥 **Групова статистика:**\n\n"
    stats += f"👤 Всього користувачів: {users_count}\n"
    stats += f"📊 Ти серед активних користувачів бота!\n\n"
    stats += f"💡 Більше групових функцій буде додано пізніше."
    
    await message.answer(stats, parse_mode="Markdown")

@dp.message(Command("settings"))
async def cmd_settings(message: Message):
    """Команда /settings - налаштування"""
    settings_text = """
⚙️ **Налаштування бота:**

Поточні налаштування:
• Нагадування: кожні 60 хвилин
• Часовий пояс: Europe/Kiev
• Час підсумку дня: 23:00
• Трекінг настрою: увімкнено
• Ціль по воді: 8 склянок на день
• Мова: українська

🎯 **Цілі:**
• Спорт: 3 рази на тиждень
• Без солодкого: 5 днів поспіль

💡 Для зміни налаштувань напиши адміністратору або використай веб-інтерфейс (буде додано пізніше).
    """
    
    await message.answer(settings_text, parse_mode="Markdown")

@dp.message()
async def handle_activity(message: Message):
    """Обробка звичайних повідомлень як активностей"""
    try:
        user = await UserManager.get_or_create_user(message.from_user)
        user_id = str(message.from_user.id)
        
        # Перевіряємо, чи це команда настрою
        if message.text.startswith('/mood '):
            parts = message.text[6:].split(' ', 1)
            mood = parts[0]
            note = parts[1] if len(parts) > 1 else ""
            
            await MoodTracker.save_mood(user_id, mood, note)
            await message.answer(f"😊 Записав твій настрій: {mood}")
            return
        
        # Звичайна обробка активності
        activity_data = await tracker.detect_activity_type(message.text)

        await UserManager.save_activity(
            user_id,
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
        
        # Перевіряємо нагадування
        await check_reminders(user_id, message)

    except Exception as e:
        logger.error(f"Помилка при обробці активності: {e}")
        await message.answer("❌ Виникла помилка при збереженні активності. Спробуй ще раз.")

async def check_reminders(user_id: str, message: Message):
    """Перевіряє та надсилає нагадування"""
    try:
        # Перевіряємо неактивність
        if await ReminderManager.check_inactivity(user_id):
            if random.random() < 0.1:  # 10% шанс нагадування
                await message.answer("⏰ Ти давно нічого не записував. Як справи? Може, час зробити перерву або випити води? 💧")
        
        # Перевіряємо настрій
        if await ReminderManager.should_ask_mood(user_id):
            if random.random() < 0.2:  # 20% шанс запитати про настрій
                await message.answer("😊 Як твій настрій сьогодні? Використай /mood щоб записати!")
        
    except Exception as e:
        logger.error(f"Помилка при перевірці нагадувань: {e}")

async def main():
    """Запуск бота"""
    logger.info("Запускаю бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
