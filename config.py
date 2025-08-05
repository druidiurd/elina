import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # Abacus AI
    ABACUS_API_KEY = os.getenv('ABACUS_API_KEY')
    ABACUS_API_URL = "https://api.abacus.ai/chatllm/v1/chat"

    # Firebase
    FIREBASE_CREDENTIALS_PATH = os.getenv('FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json')

    # Налаштування за замовчуванням
    DEFAULT_REMINDER_INTERVAL = 60  # хвилини
    DEFAULT_SUMMARY_TIME = "23:00"
    DEFAULT_TIMEZONE = "Europe/Kiev"
    DEFAULT_WATER_GOAL = 8  # склянок

    # Підтримувані мови
    SUPPORTED_LANGUAGES = ['uk', 'en']

    # Категорії активностей
    ACTIVITY_CATEGORIES = {
        'meal': {
            'emoji': '🍽',
            'subtypes': ['breakfast', 'lunch', 'dinner', 'snack']
        },
        'work': {
            'emoji': '💼',
            'subtypes': ['meeting', 'coding', 'planning', 'email']
        },
        'exercise': {
            'emoji': '💪',
            'subtypes': ['cardio', 'strength', 'yoga', 'walking']
        },
        'rest': {
            'emoji': '😴',
            'subtypes': ['sleep', 'break', 'entertainment', 'reading']
        },
        'cleaning': {
            'emoji': '🧹',
            'subtypes': ['dishes', 'laundry', 'organizing', 'general']
        },
        'meeting': {
            'emoji': '👥',
            'subtypes': ['friends', 'family', 'colleagues', 'date']
        },
        'drink': {
            'emoji': '🥤',
            'subtypes': ['water', 'coffee', 'tea', 'other']
        },
        'other': {
            'emoji': '📝',
            'subtypes': []
        }
    }
