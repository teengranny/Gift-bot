# ============================================================
# ГЕНЕРАТОР ИДЕЙ ПОДАРКОВ — TELEGRAM BOT
# Запуск: python app.py
# Требуется: pip install python-telegram-bot==21.10 flask
# Переменная окружения: TELEGRAM_BOT_TOKEN
# ============================================================

import logging
import os
import random
import asyncio
import threading

from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    filters,
)

# ============================================================
# Flask-сервер для healthcheck (чтобы Render не убивал процесс)
# ============================================================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!", 200

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

# ============================================================
# Хранилище для счётчиков и статуса премиум (в памяти)
# ============================================================
user_requests = {}      # user_id -> количество использованных бесплатных идей
user_premium = {}       # user_id -> True/False
MAX_FREE = 5

# ============================================================
# БАЗА ПОДАРКОВ
# ============================================================
GIFTS_DB = {
    "man": [
        {"title": "Умные часы с функцией мониторинга здоровья", "emoji": "⌚", "priceType": "premium", "description": "Подойдут для отслеживания физической активности и контроля показателей здоровья — полезно для тех, кто ведёт активный образ жизни.", "ozonLink": "https://takprdm.ru/0W944W82VmCiW7u0/?redirectTo=https%3A%2F%2Fwww.wildberries.ru%2Fcatalog%2F117603041%2Fdetail.aspx&erid=Y1jgkD6uB6jK1phqkTLTbNJPiD1a"},
        {"title": "Набор инструментов в кейсе", "emoji": "🔧", "priceType": "middle", "description": "Практичный подарок для домашнего мастера — поможет справиться с бытовыми задачами и организовать хранение мелочей.", "ozonLink": "https://takprdm.ru/0W944W82VmChQ0C0/?redirectTo=https%3A%2F%2Fwww.wildberries.ru%2Fcatalog%2F49844802%2Fdetail.aspx&erid=Y1jgkD6uB6jK1phqkTLTbNJPiD1a"},
        {"title": "Термокружка с подогревом от USB", "emoji": "🥤", "priceType": "budget", "description": "Удобна в дороге и на работе — позволяет наслаждаться горячим напитком в любое время.", "ozonLink": "https://ozon.ru/click/usb_heated_mug"},
        {"title": "Беспроводные наушники с шумоподавлением", "emoji": "🎧", "priceType": "middle", "description": "Идеальны для прослушивания музыки и разговоров — обеспечат комфорт в транспорте и офисе.", "ozonLink": "https://ozon.ru/click/wireless_noise_cancelling"},
        {"title": "Кожаный портфель для документов", "emoji": "💼", "priceType": "premium", "description": "Стильный аксессуар для делового человека — подчеркнёт статус и поможет организовать рабочие материалы.", "ozonLink": "https://ozon.ru/click/leather_briefcase"},
        {"title": "Набор для барбекю с аксессуарами", "emoji": "🍖", "priceType": "middle", "description": "Порадует любителя отдыха на природе — сделает пикники ещё приятнее и удобнее.", "ozonLink": "https://ozon.ru/click/bbq_tool_set"},
        {"title": "Подписка на стриминговый сервис", "emoji": "🎬", "priceType": "budget", "description": "Подарит доступ к разнообразному контенту — подойдёт для расслабления после рабочего дня.", "ozonLink": "https://ozon.ru/click/streaming_subscription"},
        {"title": "Фитнес‑браслет с отслеживанием сна", "emoji": "⌚", "priceType": "middle", "description": "Поможет следить за качеством отдыха и физической активностью — хороший выбор для заботы о здоровье.", "ozonLink": "https://ozon.ru/click/fitness_tracker_sleep"},
    ],
    "woman": [
        {"title": "Набор косметики премиум‑бренда", "emoji": "💄", "priceType": "premium", "description": "Порадует ценительницу ухода за собой — включает средства для разных этапов бьюти‑рутины.", "ozonLink": "https://ozon.ru/click/premium_cosmetics_set"},
        {"title": "Шарф из кашемира", "emoji": "🧣", "priceType": "middle", "description": "Стильный и тёплый аксессуар на холодное время года — добавит элегантности любому образу.", "ozonLink": "https://ozon.ru/click/cashmere_scarf"},
        {"title": "Аромадиффузор с набором эфирных масел", "emoji": "🕯️", "priceType": "middle", "description": "Создаст уютную атмосферу дома — поможет расслабиться и улучшить настроение.", "ozonLink": "https://ozon.ru/click/aroma_diffuser_oils"},
        {"title": "Книга любимого автора в коллекционном издании", "emoji": "📖", "priceType": "budget", "description": "Для любительницы чтения — порадует красивым оформлением и содержанием.", "ozonLink": "https://ozon.ru/click/collector_book"},
        {"title": "Набор для домашнего спа", "emoji": "🧴", "priceType": "middle", "description": "Позволит устроить салонный уход дома — идеальный вариант для релаксации.", "ozonLink": "https://ozon.ru/click/home_spa_kit"},
        {"title": "Сумка‑тоут из экокожи", "emoji": "👜", "priceType": "premium", "description": "Вместительная и стильная — подойдёт для работы и прогулок, дополнит гардероб.", "ozonLink": "https://ozon.ru/click/eco_leather_tote"},
        {"title": "Умное зеркало для макияжа с подсветкой", "emoji": "🪞", "priceType": "premium", "description": "Облегчит нанесение косметики — пригодится для точного нанесения макияжа в любых условиях.", "ozonLink": "https://ozon.ru/click/smart_makeup_mirror"},
        {"title": "Набор ароматических свечей ручной работы", "emoji": "🕯️", "priceType": "budget", "description": "Создаст романтическую атмосферу — украсит интерьер и наполнит дом приятным ароматом.", "ozonLink": "https://ozon.ru/click/handmade_candles_set"},
    ],
    "child": [
        {"title": "Конструктор с элементами дополненной реальности", "emoji": "🧩", "priceType": "middle", "description": "Развивает логику и воображение — совмещает игру с современными технологиями.", "ozonLink": "https://ozon.ru/click/ar_construction_set"},
        {"title": "Велосипед с дополнительными колёсами", "emoji": "🚲", "priceType": "middle", "description": "Для активного отдыха на свежем воздухе — поможет научиться кататься и укрепить здоровье.", "ozonLink": "https://ozon.ru/click/bike_training_wheels"},
        {"title": "Набор для научных экспериментов", "emoji": "🔬", "priceType": "budget", "description": "Пробудит интерес к науке — позволит провести увлекательные опыты дома под присмотром взрослых.", "ozonLink": "https://ozon.ru/click/science_experiment_kit"},
        {"title": "Интерактивная игрушка‑робот", "emoji": "🤖", "priceType": "middle", "description": "Развлечёт и обучит основам программирования — подойдёт для развития алгоритмического мышления.", "ozonLink": "https://ozon.ru/click/interactive_robot"},
        {"title": "Настольная игра для всей семьи", "emoji": "🎲", "priceType": "budget", "description": "Укрепит общение и научит стратегическому мышлению — разнообразит вечера и сплотит семью.", "ozonLink": "https://ozon.ru/click/family_board_game"},
        {"title": "Рюкзак с 3D‑принтом любимого персонажа", "emoji": "🎒", "priceType": "budget", "description": "Поднимет настроение и пригодится в школе — яркий и практичный аксессуар.", "ozonLink": "https://ozon.ru/click/character_backpack"},
        {"title": "Набор для рисования светом", "emoji": "✨", "priceType": "middle", "description": "Откроет новые творческие возможности — позволит создавать необычные картины и развивать фантазию.", "ozonLink": "https://ozon.ru/click/light_drawing_set"},
        {"title": "Самокат с подсветкой колёс", "emoji": "🛴", "priceType": "middle", "description": "Подарит радость от катания вечером — безопасный и стильный транспорт для прогулок.", "ozonLink": "https://ozon.ru/click/light_up_scooter"},
    ],
    "colleague": [
        {"title": "Беспроводная зарядная станция", "emoji": "🔋", "priceType": "middle", "description": "Упростит зарядку гаджетов на рабочем месте — сэкономит время и освободит пространство от проводов.", "ozonLink": "https://ozon.ru/click/wireless_charging_station"},
        {"title": "Ежедневник с персонализированной обложкой", "emoji": "📓", "priceType": "budget", "description": "Поможет организовать рабочий график — практичный инструмент для планирования задач.", "ozonLink": "https://ozon.ru/click/personalized_notebook"},
        {"title": "Кружка‑хамелеон", "emoji": "☕", "priceType": "budget", "description": "Добавит позитива в перерывы на кофе — меняет цвет при нагревании, поднимает настроение.", "ozonLink": "https://takprdm.ru/0W944W82VmCiLsm0/?redirectTo=https%3A%2F%2Fwww.wildberries.ru%2Fcatalog%2F15462468%2Fdetail.aspx&erid=Y1jgkD6uB6jK1phqkTLTbNJPiD1a"},
        {"title": "Набор качественных ручек и маркеров", "emoji": "✒️", "priceType": "budget", "description": "Пригодится для работы с документами — надёжный инструмент для заметок и презентаций.", "ozonLink": "https://ozon.ru/click/premium_pens_set"},
        {"title": "Мини‑увлажнитель воздуха для рабочего стола", "emoji": "💨", "priceType": "middle", "description": "Улучшит микроклимат в офисе — поможет сохранить комфорт в течение дня.", "ozonLink": "https://ozon.ru/click/desktop_humidifier"},
        {"title": "Подставка для ног эргономичной формы", "emoji": "🦶", "priceType": "middle", "description": "Снизит нагрузку при долгой работе за компьютером — повысит комфорт и заботу о здоровье.", "ozonLink": "https://ozon.ru/click/foot_rest_ergonomic"},
        {"title": "Портативная колонка с Bluetooth", "emoji": "🔊", "priceType": "middle", "description": "Разнообразит перерывы и встречи — позволит слушать музыку или проводить аудиоконференции.", "ozonLink": "https://ozon.ru/click/bluetooth_speaker"},
        {"title": "Подарочный сертификат в книжный магазин", "emoji": "🎁", "priceType": "budget", "description": "Даст возможность выбрать то, что действительно нужно — универсальный вариант для коллеги с любыми интересами.", "ozonLink": "https://ozon.ru/click/bookstore_gift_card"},
    ],
}

PRICE_LABELS = {
    "budget": "бюджетная",
    "middle": "средняя",
    "premium": "премиум",
}

CATEGORIES = {
    "man": "👔 Мужчине",
    "woman": "🌸 Женщине",
    "child": "🧸 Ребёнку",
    "colleague": "🤝 Коллеге",
}

def get_random_gift(category: str) -> dict:
    gifts = GIFTS_DB.get(category, [])
    if not gifts:
        return {"title": "Скоро добавим идеи", "emoji": "🎁", "priceType": "", "description": "Пожалуйста, выберите другую категорию.", "ozonLink": "https://ozon.ru/"}
    return random.choice(gifts)

def format_gift_message(gift: dict) -> str:
    price_label = PRICE_LABELS.get(gift.get("priceType", ""), "")
    price_line = f"💰 Стоимость: {price_label}\n" if price_label else ""
    return f"{gift['emoji']} *{gift['title']}*\n{price_line}\n{gift['description']}\n\n[Купить →]({gift['ozonLink']})"

def build_category_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(label, callback_data=f"cat:{key}")] for key, label in CATEGORIES.items()]
    return InlineKeyboardMarkup(buttons)

def build_gift_keyboard(category: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Ещё идея", callback_data=f"cat:{category}")],
        [InlineKeyboardButton("↩️ Выбрать категорию", callback_data="menu")],
    ])

async def start(update: Update, context) -> None:
    # При новом старте сбрасываем счётчик пользователя (по желанию)
    user_id = update.effective_user.id
    if user_id not in user_requests:
        user_requests[user_id] = 0
    await update.message.reply_text(
        "🎁 *Подарочный гуру*\n\nПривет! Я помогу тебе выбрать подарок.\n"
        "У тебя есть 5 бесплатных идей. После этого можно купить Премиум за 199 ₽ и пользоваться безлимитом.\n\n"
        "Выбери категорию:",
        parse_mode="Markdown",
        reply_markup=build_category_keyboard(),
    )

async def help_command(update: Update, context) -> None:
    await update.message.reply_text(
        "🎁 *Подарочный гуру*\n\n"
        "Команды:\n"
        "/start — показать меню выбора категории\n"
        "/help — это сообщение\n"
        "/premium — купить безлимит за 199 ₽\n\n"
        "Бесплатных идей — 5. Премиум даёт безлимит, фильтры и сохранение списка.",
        parse_mode="Markdown",
    )

async def premium(update: Update, context) -> None:
    await update.message.reply_text(
        "✨ *Премиум-доступ* ✨\n\n"
        "💰 Стоимость: *199 рублей* (единоразово)\n\n"
        "Что вы получите:\n"
        "✅ *Безлимит идей* подарков\n"
        "✅ *Фильтр по бюджету* (бюджетный, средний, премиум)\n"
        "✅ *Сохранение понравившихся идей*\n\n"
        "Скоро оплата будет доступна. Следите за обновлениями!\n\n"
        "А пока можете продолжать пользоваться бесплатными идеями (осталось их счётчик).",
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    # Проверяем, премиум ли пользователь
    if user_premium.get(user_id, False):
        premium_active = True
    else:
        premium_active = False

    if data == "menu":
        await query.edit_message_text(
            "🎁 *Подарочный гуру*\n\nВыберите категорию:",
            parse_mode="Markdown",
            reply_markup=build_category_keyboard(),
        )
        return

    if data.startswith("cat:"):
        category = data.split(":", 1)[1]

        # Если не премиум, проверяем лимит
        if not premium_active:
            # Получаем текущее количество использованных бесплатных идей
            count = user_requests.get(user_id, 0)
            if count >= MAX_FREE:
                await query.edit_message_text(
                    "❌ *Лимит бесплатных идей исчерпан!*\n\n"
                    "У вас было 5 бесплатных идей. Чтобы получать безлимит, оформите Премиум:\n"
                    "💰 *199 рублей* — навсегда.\n\n"
                    "Нажмите /premium, чтобы узнать подробности.",
                    parse_mode="Markdown",
                    reply_markup=build_category_keyboard(),
                )
                return
            # Увеличиваем счётчик
            user_requests[user_id] = count + 1

        # Выдаём идею
        gift = get_random_gift(category)
        category_label = CATEGORIES.get(category, category)
        text = f"*Идея подарка — {category_label}*\n\n{format_gift_message(gift)}"
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=build_gift_keyboard(category),
            disable_web_page_preview=True,
        )

async def error_handler(update: object, context) -> None:
    if isinstance(context.error, Conflict):
        logger.warning("Conflict: another bot instance is running with this token. Retrying... (stop the other instance to resolve this)")
    else:
        logger.error("Unhandled error: %s", context.error, exc_info=context.error)

# ============================================================
# ЗАПУСК
# ============================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is not set.")

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("premium", premium))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
