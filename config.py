import os

# Проверяем, запущен ли бот на Railway с Volume
if os.path.exists("/app/data"):
    DATABASE_PATH = "/app/data/art_collector.db"
    CARDS_FOLDER = "/app/data/cards"
else:
    DATABASE_PATH = "art_collector.db"
    CARDS_FOLDER = "cards"

BOT_TOKEN = "8912673889:AAEkd6SlbKSm0dG5oXXHvIa1aTS9Qm3lLGE"
ADMIN_IDS = [6782892398]
import os
CARD_COOLDOWN_HOURS = 4
START_COINS = 100
DAILY_COINS = 50

# Редкости и шансы (в сумме должно быть 100%)
RARITIES = {
    "common": {"chance": 49.99, "color": "⚪", "multiplier": 1},
    "rare": {"chance": 25, "color": "🔵", "multiplier": 3},
    "epic": {"chance": 15, "color": "🟣", "multiplier": 10},
    "legendary": {"chance": 9, "color": "🟡", "multiplier": 50},
    "secret": {"chance": 1, "color": "🔴", "multiplier": 100},
    "mythical": {"chance": 0.01, "color": "🟣✨", "multiplier": 500}  # НОВАЯ РЕДКОСТЬ!
}


CARDS_JSON = "cards.json"

# Streak-система
STREAK_REWARDS = {
    1: {"coins": 50, "description": "Первый день"},
    3: {"coins": 100, "description": "3 дня подряд 🔥"},
    7: {"coins": 250, "description": "Неделя подряд 🔥🔥"},
    14: {"coins": 500, "description": "2 недели подряд 🔥🔥🔥"},
    30: {"coins": 1000, "description": "Месяц подряд 💎"},
    100: {"coins": 5000, "description": "100 дней! ЛЕГЕНДА! 👑"}
}

# Магазин
SHOP_ITEMS = {
    "skip": {
        "name": "⏭️ Пропуск",
        "description": "Пропускает кулдаун один раз",
        "price": 250,
        "type": "consumable",
        "effect": "skip_cooldown"
    },
    "timer": {
        "name": "⏱️ Таймер",
        "description": "Снижает кулдаун на 30 минут навсегда",
        "price": 2000,
        "type": "permanent",
        "effect": "cooldown_minus_30min"
    },
    "gold_timer": {
        "name": "🏆 Золотой таймер",
        "description": "Снижает кулдаун на 2 часа навсегда",
        "price": 7500,
        "type": "permanent",
        "effect": "cooldown_minus_2h"
    },
    "pack": {
        "name": "📦 Пакет",
        "description": "Позволяет получать 2 карточки за один кулдаун (вместо 1)",
        "price": 12000,
        "type": "permanent",
        "effect": "double_claim"
    },
    "pack_normal": {
        "name": "📦 Обычный набор",
        "description": "2-3 случайные карточки (макс. редкость: Rare)",
        "price": 200,
        "type": "consumable",
        "effect": "card_pack",
        "pack_config": {"min": 2, "max": 3, "max_rarity": "rare", "secret_chance": 0}
    },
    "pack_pro": {
        "name": "💼 Профессиональный набор",
        "description": "4-6 карточек (макс. редкость: Legendary, шанс низкий)",
        "price": 1000,
        "type": "consumable",
        "effect": "card_pack",
        "pack_config": {"min": 4, "max": 6, "max_rarity": "legendary", "secret_chance": 0}
    },
    "pack_premium": {
        "name": "👑 Премиум набор",
        "description": "8-12 карточек (повышенный шанс на Secret: 1.4%)",
        "price": 4500,
        "type": "consumable",
        "effect": "card_pack",
        "pack_config": {"min": 8, "max": 12, "max_rarity": "secret", "secret_chance": 1.4}
    }
}

# Кейсы
CASES = {
    "wooden": {
        "name": "🪵 Деревянный кейс",
        "description": "1-2 карточки (Common/Rare) + шанс на Пропуск",
        "price": 120,
        "cards": {"min": 1, "max": 2, "max_rarity": "rare", "secret_chance": 0},
        "items": [
            {"item": "skip", "chance": 15}
        ]
    },
    "iron": {
        "name": "⚙️ Железный кейс",
        "description": "2-3 карточки (Rare/Epic) + шанс на Таймер",
        "price": 400,
        "cards": {"min": 2, "max": 3, "max_rarity": "epic", "secret_chance": 0},
        "items": [
            {"item": "skip", "chance": 20},
            {"item": "timer", "chance": 5}
        ]
    },
    "gold": {
        "name": "🥇 Золотой кейс",
        "description": "3-5 карточек (Epic/Legendary) + шанс на Пропуск/Таймер",
        "price": 1200,
        "cards": {"min": 3, "max": 5, "max_rarity": "legendary", "secret_chance": 0},
        "items": [
            {"item": "skip", "chance": 25},
            {"item": "timer", "chance": 10},
            {"item": "pack_normal", "chance": 5}
        ]
    },
    "platinum": {
        "name": "💎 Платиновый кейс",
        "description": "5-8 карточек (Legendary+) + шанс на Золотой таймер/Пакет",
        "price": 3500,
        "cards": {"min": 5, "max": 8, "max_rarity": "legendary", "secret_chance": 0.5},
        "items": [
            {"item": "skip", "chance": 30},
            {"item": "timer", "chance": 15},
            {"item": "gold_timer", "chance": 5},
            {"item": "pack_pro", "chance": 8},
            {"item": "pack", "chance": 2}
        ]
    },
    "crystal": {
        "name": "💠 Кристальный кейс",
        "description": "8-12 карточек (повышенный шанс Secret) + шанс на Пакет",
        "price": 8000,
        "cards": {"min": 8, "max": 12, "max_rarity": "secret", "secret_chance": 2.0},
        "items": [
            {"item": "skip", "chance": 40},
            {"item": "timer", "chance": 20},
            {"item": "gold_timer", "chance": 10},
            {"item": "pack", "chance": 5},
            {"item": "pack_premium", "chance": 15}
        ]
    }
}

# Ежедневные задания
DAILY_TASKS = {
    "claim_1": {
        "name": "🎨 Первая карточка",
        "description": "Получи 1 карточку сегодня",
        "target": 1,
        "reward": 30,
        "type": "claim"
    },
    "claim_3": {
        "name": "🎨 Три карточки",
        "description": "Получи 3 карточки сегодня",
        "target": 3,
        "reward": 100,
        "type": "claim"
    },
    "claim_5": {
        "name": "🎨 Пять карточек",
        "description": "Получи 5 карточек сегодня",
        "target": 5,
        "reward": 200,
        "type": "claim"
    },
    "trade_1": {
        "name": "💱 Первый обмен",
        "description": "Соверши 1 обмен сегодня",
        "target": 1,
        "reward": 50,
        "type": "trade"
    },
    "trade_3": {
        "name": "💱 Три обмена",
        "description": "Соверши 3 обмена сегодня",
        "target": 3,
        "reward": 150,
        "type": "trade"
    },
    "promo_1": {
        "name": "🎟️ Активация промокода",
        "description": "Активируй 1 промокод сегодня",
        "target": 1,
        "reward": 40,
        "type": "promo"
    },
    "view_3": {
        "name": "👁️ Исследователь",
        "description": "Просмотри 3 чужие коллекции",
        "target": 3,
        "reward": 60,
        "type": "view"
    },
    "daily_1": {
        "name": "📅 Ежедневный бонус",
        "description": "Получи ежедневный бонус",
        "target": 1,
        "reward": 25,
        "type": "daily"
    },
    "shop_1": {
        "name": "🛒 Первая покупка",
        "description": "Купи что-нибудь в магазине",
        "target": 1,
        "reward": 50,
        "type": "shop"
    }
}

ACHIEVEMENTS = {
    "first_card": {
        "name": "🎨 Первая карточка",
        "description": "Получи свою первую карточку",
        "reward": 50,
        "check": lambda stats: stats["unique"] >= 1
    },
    "collector_5": {
        "name": "📚 Начинающий коллекционер",
        "description": "Собери 5 уникальных карточек",
        "reward": 100,
        "check": lambda stats: stats["unique"] >= 5
    },
    "collector_10": {
        "name": "🏆 Коллекционер",
        "description": "Собери 10 уникальных карточек",
        "reward": 200,
        "check": lambda stats: stats["unique"] >= 10
    },
    "collector_25": {
        "name": "👑 Мастер коллекции",
        "description": "Собери 25 уникальных карточек",
        "reward": 500,
        "check": lambda stats: stats["unique"] >= 25
    },
    "first_legendary": {
        "name": "✨ Первая легенда",
        "description": "Получи первую Legendary карточку",
        "reward": 300,
        "check": lambda stats: stats["rarity_stats"].get("legendary", 0) >= 1
    },
    "first_secret": {
        "name": "🔴 Секрет найден!",
        "description": "Получи секретную карточку",
        "reward": 1000,
        "check": lambda stats: stats["rarity_stats"].get("secret", 0) >= 1
    },
    "first_mythical": {
        "name": "🟣✨ Мифическая находка!",
        "description": "Получи мифическую карточку (шанс 0.01%)",
        "reward": 5000,
        "check": lambda stats: stats["rarity_stats"].get("mythical", 0) >= 1
    },
    "trader_1": {
        "name": "💱 Первый обмен",
        "description": "Соверши первый обмен",
        "reward": 100,
        "check": lambda stats: stats.get("trades", 0) >= 1
    },
    "trader_10": {
        "name": "🤝 Опытный трейдер",
        "description": "Соверши 10 обменов",
        "reward": 300,
        "check": lambda stats: stats.get("trades", 0) >= 10
    },
    "rich_1000": {
        "name": "💰 Тысячник",
        "description": "Накопи 1000 монет",
        "reward": 200,
        "check": lambda stats: stats.get("coins", 0) >= 1000
    },
    "rich_10000": {
        "name": "💎 Богач",
        "description": "Накопи 10000 монет",
        "reward": 1000,
        "check": lambda stats: stats.get("coins", 0) >= 10000
    },
    "streak_7": {
        "name": "🔥 Неделя без пропусков",
        "description": "Заходи 7 дней подряд",
        "reward": 500,
        "check": lambda stats: stats.get("streak", 0) >= 7
    },
    "streak_30": {
        "name": "🌟 Месяц без пропусков",
        "description": "Заходи 30 дней подряд",
        "reward": 2000,
        "check": lambda stats: stats.get("streak", 0) >= 30
    },
    "tasks_5": {
        "name": "📋 Выполняющий задания",
        "description": "Выполни 5 ежедневных заданий",
        "reward": 250,
        "check": lambda stats: stats.get("tasks_completed", 0) >= 5
    },
    "tasks_20": {
        "name": "🏅 Мастер заданий",
        "description": "Выполни 20 ежедневных заданий",
        "reward": 1000,
        "check": lambda stats: stats.get("tasks_completed", 0) >= 20
    },
    "shopper_1": {
        "name": "🛒 Первая покупка",
        "description": "Купи что-нибудь в магазине",
        "reward": 100,
        "check": lambda stats: stats.get("shop_purchases", 0) >= 1
    },
    "shopper_10": {
        "name": "🏪 Постоянный клиент",
        "description": "Соверши 10 покупок в магазине",
        "reward": 500,
        "check": lambda stats: stats.get("shop_purchases", 0) >= 10
    },
    "market_seller_1": {
        "name": "🏪 Первый продавец",
        "description": "Продай карточку на рынке",
        "reward": 200,
        "check": lambda stats: stats.get("market_sales", 0) >= 1
    }
}

# Стикеры для событий (замени file_id на свои)
STICKERS = {
    "secret_card": "CAACAgIAAxkBAAIB",
    "legendary_card": "CAACAgIAAxkBAAIC",
    "mythical_card": "CAACAgIAAxkBAAIK",  # НОВЫЙ СТИКЕР ДЛЯ МИФИЧЕСКОЙ
    "achievement": "CAACAgIAAxkBAAID",
    "case_open": "CAACAgIAAxkBAAIE",
    "streak_7": "CAACAgIAAxkBAAIF",
    "streak_30": "CAACAgIAAxkBAAIG",
    "promo": "CAACAgIAAxkBAAIH",
    "daily": "CAACAgIAAxkBAAII",
    "welcome": "CAACAgIAAxkBAAIJ",
}# === РЕФЕРАЛЬНАЯ СИСТЕМА ===
REFERRAL_BONUS_INVITEE = 200  # Бонус тому, кто перешел по ссылке
REFERRAL_BONUS_INVITER = 300  # Бонус тому, кто пригласил

# === СЕЗОННЫЕ КОЛЛЕКЦИИ ===
# Если ACTIVE_SEASON не None, то при /claim есть шанс получить сезонную карточку
ACTIVE_SEASON = "winter_2026"  # Например: "winter_2026", "summer_2026" или None
SEASONAL_DROP_CHANCE = 5  # Шанс 5% получить сезонную карточку вместо обычной

# === АУКЦИОНЫ ===
AUCTION_DURATION_HOURS = 24  # Сколько длится аукцион по умолчанию
AUCTION_MIN_BID_INCREMENT = 50  # Минимальный шаг ставки
AUCTION_FEE_PERCENT = 10  # Комиссия с продажи (как было на рынке)
