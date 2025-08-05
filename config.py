import os
from dotenv import load_dotenv

# Завантажуємо змінні з .env файлу (якщо є)
load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "8285203127:AAGIvOvSzctyegI3-olZKSqd5KYq55898E8")

# Abacus AI
ABACUS_API_KEY = os.getenv("ABACUS_API_KEY",
                           "s2_7ef3d5d6f29246498d2c929662499308")
ABACUS_API_URL = "https://api.abacus.ai/chatllm/v1/chat"

# Firebase
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "serviceAccountKey.json")

# Налаштування за замовчуванням
DEFAULT_TIMEZONE = "Europe/Kiev"
DEFAULT_LANGUAGE = "uk"
DEFAULT_REMINDER_INTERVAL = 60  # хвилин
DEFAULT_WATER_GOAL = 8  # склянок на день
DEFAULT_SUMMARY_TIME = "23:00"

# Налаштування логування
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Налаштування AI
AI_MODEL = "claude-3-sonnet"
AI_TIMEOUT = 30  # секунд


class Config:
  ABACUS_API_KEY = os.getenv("ABACUS_API_KEY",
                             "s2_7ef3d5d6f29246498d2c929662499308")
  ABACUS_API_URL = "https://api.abacus.ai/chatllm/v1/chat"
