import re
from datetime import datetime
from typing import Dict
from aiogram import types
from firebase_admin import firestore

# Отримуємо клієнт Firestore (буде ініціалізований в bot.py)
db = None


def init_db(firestore_client):
    """Ініціалізує клієнт Firestore"""
    global db
    db = firestore_client


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
    async def get_daily_stats(user_id: str, db):
        today = datetime.now().strftime('%Y-%m-%d')
        activities_ref = db.collection('activities')
        query = activities_ref.where('user_id', '==',
                                     user_id).where('date', '==', today)
        docs = query.stream()

        stats = {}
        total = 0
        for doc in docs:
            data = doc.to_dict()
            act_type = data.get('type', 'other')
            stats[act_type] = stats.get(act_type, 0) + 1
            total += 1

        return stats, total

    @staticmethod
    async def save_activity(user_id: str, activity_data: Dict, raw_text: str):
        """Зберігає активність в Firestore"""
        now = datetime.utcnow()

        # Парсимо час з повідомлення
        time_match = re.match(r'^(\d{1,2}):(\d{2})', raw_text.strip())
        if time_match:
            hour, minute = int(time_match.group(1)), int(time_match.group(2))
            today = datetime.now().date()
            activity_time = datetime.combine(
                today,
                datetime.min.time().replace(hour=hour, minute=minute))
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
