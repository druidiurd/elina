import re
import json
import requests
from config import Config
import logging

logger = logging.getLogger(__name__)

class ActivityTracker:
    def __init__(self):
        self.activity_types = {
            'meal': ['їм', 'обід', 'сніданок', 'вечеря', 'перекус', 'готую', 'роблю обід'],
            'work': ['робота', 'працюю', 'зустріч', 'мітинг', 'проект', 'завдання'],
            'exercise': ['спорт', 'тренування', 'біг', 'присідання', 'віджимання', 'зал'],
            'rest': ['відпочинок', 'перерва', 'дивлюся', 'читаю', 'слухаю'],
            'cleaning': ['прибирання', 'миття', 'прання', 'порядок'],
            'meeting': ['зустріч з', 'бачився з', 'розмова з'],
            'drink': ['п\'ю', 'випив', 'кава', 'чай', 'вода'],
            'sleep': ['спати', 'лягаю спати', 'йду спати', 'сон', 'відпочивати', 'засинаю']  # ДОДАНО
        }

    async def detect_activity_type(self, text: str) -> dict:
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

    async def _extract_details(self, text: str, activity_type: str) -> dict:
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

        elif activity_type == 'sleep':  # ДОДАНО
            details['subtype'] = 'sleep'
            # Можна додати додаткову обробку, наприклад, "нічний сон" чи "денний сон" за часом

        return details

    async def _extract_food_items(self, text: str) -> list:
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

    async def _extract_exercise_info(self, text: str) -> dict:
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

    def _extract_people(self, text: str) -> list:
        """Витягує імена людей з тексту"""
        people = []
        if ' з ' in text.lower():
            parts = text.lower().split(' з ')
            if len(parts) > 1:
                person = parts[1].split()[0]
                people.append(person)

        return people

    def _extract_drink_info(self, text: str) -> dict:
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

    async def _analyze_with_ai(self, text: str) -> dict:
        """Використовує Abacus ChatLLM API для аналізу складних активностей"""
        try:
            prompt = f"""
            Проаналізуй цю активність користувача і визнач:
            1. Тип активності (meal, work, rest, meeting, cleaning, exercise, drink, sleep, other)
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
                Config.ABACUS_API_URL,
                headers={
                    'Authorization': f'Bearer {Config.ABACUS_API_KEY}',
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