from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === ГЛАВНОЕ МЕНЮ ===
def main_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎨 Получить карточку", callback_data="claim_card"),
            InlineKeyboardButton(text="📚 Моя коллекция", callback_data="collection")
        ],
        [
            InlineKeyboardButton(text="🔥 Серия дней", callback_data="streak_info"),
            InlineKeyboardButton(text="🏅 Рейтинг", callback_data="leaderboard")
        ],
        [
            InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton(text="📋 Задания", callback_data="daily_tasks"),
            InlineKeyboardButton(text="🎁 Ежедневный бонус", callback_data="daily_from_streak")
        ],
        [
            InlineKeyboardButton(text="🛒 Магазин", callback_data="shop_main"),
            InlineKeyboardButton(text="🏪 Рынок", callback_data="market_main")
        ],
        [
            InlineKeyboardButton(text="🔨 Аукционы", callback_data="auction_main"),
            InlineKeyboardButton(text="💱 Обмены", callback_data="trades")
        ],
        [
            InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory"),
            InlineKeyboardButton(text="💰 Кошелёк", callback_data="wallet")
        ],
        [
            InlineKeyboardButton(text="🔍 Поиск", callback_data="search_category"),
            InlineKeyboardButton(text="🎨 Художники", callback_data="artists_list")
        ],
        [
            InlineKeyboardButton(text="🎟️ Промокод", callback_data="promo_activate"),
            InlineKeyboardButton(text="👥 Реферал", callback_data="ref_link")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ])
    return keyboard

# === НАВИГАЦИЯ ===
def back_to_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
    ])
    return keyboard

def back_to_admin_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Админ-панель", callback_data="admin_main")]
    ])
    return keyboard

# === АДМИНКА ===
def admin_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="🎴 Карточки", callback_data="admin_cards"),
            InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="🎟️ Промокоды", callback_data="admin_promo"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="◀️ Выйти", callback_data="main_menu")
        ]
    ])
    return keyboard

def admin_stats_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏆 Топ коллекционеров", callback_data="admin_top")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")
        ]
    ])
    return keyboard

def admin_users_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Список всех", callback_data="admin_users_list"),
            InlineKeyboardButton(text="🔍 Найти по ID", callback_data="admin_user_search")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")
        ]
    ])
    return keyboard

def admin_cards_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data="admin_card_add"),
            InlineKeyboardButton(text="📋 Список", callback_data="admin_card_list")
        ],
        [
            InlineKeyboardButton(text="🗑️ Удалить", callback_data="admin_card_delete")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")
        ]
    ])
    return keyboard

def admin_broadcast_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Текст", callback_data="admin_broadcast_text"),
            InlineKeyboardButton(text="🖼️ Фото + текст", callback_data="admin_broadcast_photo")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")
        ]
    ])
    return keyboard

def admin_promo_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Создать", callback_data="admin_promo_create"),
            InlineKeyboardButton(text="📋 Список", callback_data="admin_promo_list")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")
        ]
    ])
    return keyboard

# === ПРОМОКОДЫ ===
def promo_list_keyboard(promo_codes):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for promo in promo_codes[:10]:
        code, reward_type, reward_value, max_uses, current_uses, _, _, is_active = promo
        status = "✅" if is_active else "❌"
        text = f"{status} {code} ({current_uses}/{max_uses})"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=text, callback_data=f"promo_manage_{code}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promo")
    ])
    return keyboard

def promo_manage_keyboard(code, is_active):
    action = "Деактивировать" if is_active else "Активировать"
    action_callback = f"promo_deactivate_{code}" if is_active else f"promo_activate_{code}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"{'🔒' if is_active else '🔓'} {action}", callback_data=action_callback),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"promo_delete_{code}")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="admin_promo_list")
        ]
    ])
    return keyboard

# === МАГАЗИН ===
def shop_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧰 Предметы", callback_data="shop_items"),
            InlineKeyboardButton(text="📦 Наборы", callback_data="shop_packs")
        ],
        [
            InlineKeyboardButton(text="🎁 Кейсы", callback_data="shop_cases")
        ],
        [
            InlineKeyboardButton(text="🎒 Мой инвентарь", callback_data="inventory")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
        ]
    ])
    return keyboard

def shop_items_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for key, item in [
        ("skip", "⏭️ Пропуск"),
        ("timer", "⏱️ Таймер"),
        ("gold_timer", "🏆 Золотой таймер"),
        ("pack", "📦 Пакет")
    ]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=item, callback_data=f"shop_buy_{key}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="shop_main")
    ])
    return keyboard

def shop_packs_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for key, item in [
        ("pack_normal", "📦 Обычный набор"),
        ("pack_pro", "💼 Профессиональный"),
        ("pack_premium", "👑 Премиум")
    ]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=item, callback_data=f"shop_buy_{key}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="shop_main")
    ])
    return keyboard

def shop_cases_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for key, item in [
        ("wooden", "🪵 Деревянный"),
        ("iron", "⚙️ Железный"),
        ("gold", "🥇 Золотой"),
        ("platinum", "💎 Платиновый"),
        ("crystal", "💠 Кристальный")
    ]:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=item, callback_data=f"shop_buy_{key}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="shop_main")
    ])
    return keyboard

def buy_item_keyboard(item_key, price):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"💰 Купить за {price}", callback_data=f"shop_confirm_{item_key}")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="shop_items")
        ]
    ])
    return keyboard

def buy_pack_keyboard(pack_key, price):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"💰 Купить за {price}", callback_data=f"shop_confirm_{pack_key}")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="shop_packs")
        ]
    ])
    return keyboard

def buy_case_keyboard(case_key, price):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"💰 Купить за {price}", callback_data=f"shop_confirm_{case_key}")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="shop_cases")
        ]
    ])
    return keyboard

# === ИНВЕНТАРЬ ===
def inventory_keyboard(items):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if not items:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="📭 Инвентарь пуст", callback_data="shop_main")
        ])
    else:
        for item_key, quantity in items.items():
            from config import SHOP_ITEMS
            item = SHOP_ITEMS.get(item_key)
            if item:
                button_text = f"{item['name']} x{quantity}"
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=button_text, callback_data=f"inv_use_{item_key}")
                ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
    ])
    return keyboard

# === РЫНОК ===
def market_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏪 Все объявления", callback_data="market_list"),
            InlineKeyboardButton(text="📊 Мои объявления", callback_data="market_mine")
        ],
        [
            InlineKeyboardButton(text="➕ Выставить на продажу", callback_data="market_sell")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
        ]
    ])
    return keyboard

def market_sell_keyboard(collection):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for card in collection[:20]:
        card_id, count, name, artist, rarity, filename, category, *_ = card
        from config import RARITIES
        color = RARITIES.get(rarity, {}).get("color", "⚪")
        button_text = f"{color} {name} (Номер: {card_id}) x{count}"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"market_set_price_{card_id}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="market_main")
    ])
    return keyboard

def market_listing_keyboard(listing_id, is_owner):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if is_owner:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🚫 Снять с продажи", callback_data=f"market_cancel_{listing_id}")
        ])
    else:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="💰 Купить", callback_data=f"market_buy_{listing_id}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="market_list")
    ])
    return keyboard

# === ОБМЕНЫ ===
def trades_menu_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Входящие", callback_data="trades_incoming"),
            InlineKeyboardButton(text="📤 Мои предложения", callback_data="trades_outgoing")
        ],
        [
            InlineKeyboardButton(text="➕ Создать обмен", callback_data="trade_create")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
        ]
    ])
    return keyboard

def trade_create_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 По username", callback_data="trade_by_username"),
            InlineKeyboardButton(text="🆔 По ID", callback_data="trade_by_id")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="trades")
        ]
    ])
    return keyboard

def trade_offer_keyboard(offer_id, user_id, is_recipient):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if is_recipient:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="✅ Принять", callback_data=f"trade_accept_{offer_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"trade_decline_{offer_id}")
        ])
    else:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🚫 Отменить", callback_data=f"trade_cancel_{offer_id}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="trades")
    ])
    return keyboard

# === РЕЙТИНГ ===
def leaderboard_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 По карточкам", callback_data="lb_cards"),
            InlineKeyboardButton(text="💰 По монетам", callback_data="lb_coins")
        ],
        [
            InlineKeyboardButton(text="🔥 По серии", callback_data="lb_streak")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
        ]
    ])
    return keyboard

# === СЕРИЯ ДНЕЙ ===
def streak_info_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Получить бонус", callback_data="daily_from_streak")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
        ]
    ])
    return keyboard

# === ЗАДАНИЯ ===
def daily_tasks_keyboard(tasks):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for task in tasks:
        if task["completed"]:
            button_text = f"✅ {task['name']} ({task['progress']}/{task['target']})"
        else:
            button_text = f"🔄 {task['name']} ({task['progress']}/{task['target']})"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"task_claim_{task['key']}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
    ])
    return keyboard

# === ПОИСК ===
def category_filter_keyboard(categories):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    for i, category in enumerate(categories):
        row.append(InlineKeyboardButton(text=category, callback_data=f"category_{category}"))
        if len(row) == 2 or i == len(categories) - 1:
            keyboard.inline_keyboard.append(row)
            row = []
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
    ])
    return keyboard

# === КОЛЛЕКЦИЯ ===
def collection_view_keyboard(cards, current_index):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    nav_row = []
    if current_index > 0:
        nav_row.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"col_prev_{current_index}"))
    nav_row.append(InlineKeyboardButton(text=f"📊 {current_index + 1}/{len(cards)}", callback_data="noop"))
    if current_index < len(cards) - 1:
        nav_row.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"col_next_{current_index}"))
    if nav_row:
        keyboard.inline_keyboard.append(nav_row)
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")
    ])
    return keyboard

def collection_start_keyboard(has_cards):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if has_cards:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text="🖼️ Смотреть фото", callback_data="col_view_0")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")
    ])
    return keyboard