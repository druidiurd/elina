from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

class KeyboardManager:
    @staticmethod
    def main_menu():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Додати активність")],
                [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📝 Підсумок дня")],
                [KeyboardButton(text="⚙️ Налаштування")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def activity_types():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🍽 Їжа"), KeyboardButton(text="💧 Вода")],
                [KeyboardButton(text="💪 Спорт"), KeyboardButton(text="😴 Сон")],
                [KeyboardButton(text="🏢 Робота"), KeyboardButton(text="🧹 Прибирання")],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def settings_menu():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔔 Нагадування"), KeyboardButton(text="🌐 Мова")],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )

    @staticmethod
    def inline_example():
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Перейти на сайт", url="https://t.me/yourbot")]
            ]
        )
