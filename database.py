import sqlite3
from datetime import datetime, timedelta
import random
import json
import os

DB_NAME = "art_collector.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


async def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        coins INTEGER DEFAULT 0,
        last_card_time TIMESTAMP,
        daily_claimed DATE,
        trades_completed INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        current_streak INTEGER DEFAULT 0,
        best_streak INTEGER DEFAULT 0,
        last_daily DATE,
        cooldown_reduction_minutes INTEGER DEFAULT 0,
        extra_claims INTEGER DEFAULT 0
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        artist TEXT NOT NULL,
        filename TEXT NOT NULL,
        rarity TEXT NOT NULL,
        category TEXT,
        description TEXT,
        season_tag TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_cards (
        user_id INTEGER,
        card_id INTEGER,
        count INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, card_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (card_id) REFERENCES cards(id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user INTEGER,
        to_user INTEGER,
        from_card INTEGER,
        to_card INTEGER,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY (from_user) REFERENCES users(user_id),
        FOREIGN KEY (to_user) REFERENCES users(user_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS achievements (
        user_id INTEGER,
        achievement_key TEXT,
        awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, achievement_key),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS daily_tasks (
        user_id INTEGER,
        task_key TEXT,
        progress INTEGER DEFAULT 0,
        completed INTEGER DEFAULT 0,
        date DATE,
        PRIMARY KEY (user_id, task_key, date),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS promo_codes (
        code TEXT PRIMARY KEY,
        reward_type TEXT,
        reward_value INTEGER,
        max_uses INTEGER,
        current_uses INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        specific_card_id INTEGER DEFAULT NULL
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS promo_uses (
        user_id INTEGER,
        code TEXT,
        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, code),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS broadcasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        type TEXT,
        content TEXT,
        sent_count INTEGER,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS user_items (
        user_id INTEGER,
        item_key TEXT,
        quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, item_key),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        item_key TEXT,
        price INTEGER,
        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER NOT NULL,
        seller_id INTEGER NOT NULL,
        start_price INTEGER NOT NULL,
        current_bid INTEGER DEFAULT 0,
        current_bidder_id INTEGER DEFAULT NULL,
        end_time TIMESTAMP NOT NULL,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (card_id) REFERENCES cards(id),
        FOREIGN KEY (seller_id) REFERENCES users(user_id)
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER NOT NULL,
        seller_id INTEGER NOT NULL,
        price INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP,
        sold_at TIMESTAMP,
        FOREIGN KEY (card_id) REFERENCES cards(id),
        FOREIGN KEY (seller_id) REFERENCES users(user_id)
    )''')

    conn.commit()
    conn.close()

    await migrate_db()
    await load_cards_from_json()


async def migrate_db():
    conn = get_connection()
    cursor = conn.cursor()

    columns_to_add = [
        ("current_streak", "INTEGER DEFAULT 0"),
        ("best_streak", "INTEGER DEFAULT 0"),
        ("last_daily", "DATE"),
        ("cooldown_reduction_minutes", "INTEGER DEFAULT 0"),
        ("extra_claims", "INTEGER DEFAULT 0"),
    ]

    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"✅ Добавлена колонка: {col_name}")
        except Exception:
            pass

    try:
        cursor.execute("ALTER TABLE achievements ADD COLUMN awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        conn.commit()
        print("✅ Добавлена колонка: awarded_at в achievements")
    except:
        pass

    conn.close()


async def load_cards_from_json():
    if not os.path.exists('cards.json'):
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:
        with open('cards.json', 'r', encoding='utf-8') as f:
            cards_data = json.load(f)

        for card in cards_data:
            cursor.execute("SELECT id FROM cards WHERE id = ?", (card['id'],))
            if not cursor.fetchone():
                cursor.execute('''INSERT INTO cards (id, name, artist, filename, rarity, category, description, season_tag)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                               (card['id'], card['name'], card['artist'], card['filename'],
                                card['rarity'], card.get('category', ''), card.get('description', ''),
                                card.get('season_tag')))

        conn.commit()
        print(f"✅ Загружено {len(cards_data)} карточек из JSON")
    except Exception as e:
        print(f"⚠️ Ошибка загрузки cards.json: {e}")
    finally:
        conn.close()


async def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


async def create_user(user_id, username=None, referred_by=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (user_id, username, coins, registered_at) VALUES (?, ?, ?, ?)",
                       (user_id, username, 1000, datetime.now().isoformat()))
        conn.commit()

        if referred_by and referred_by != user_id:
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (referred_by,))
            if cursor.fetchone():
                cursor.execute("UPDATE users SET coins = coins + 100 WHERE user_id = ?", (referred_by,))
                cursor.execute("UPDATE users SET coins = coins + 50 WHERE user_id = ?", (user_id,))
                conn.commit()
                return True

        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


async def update_coins(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()


async def update_last_card_time(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_card_time = ? WHERE user_id = ?",
                   (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()


async def get_user_coins(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


async def get_random_card_by_rarity(rarity, season_only=False):
    conn = get_connection()
    cursor = conn.cursor()

    if season_only:
        from config import ACTIVE_SEASON
        cursor.execute("SELECT * FROM cards WHERE rarity = ? AND season_tag = ? ORDER BY RANDOM() LIMIT 1",
                       (rarity, ACTIVE_SEASON))
    else:
        cursor.execute("SELECT * FROM cards WHERE rarity = ? ORDER BY RANDOM() LIMIT 1", (rarity,))

    card = cursor.fetchone()
    conn.close()
    return card


async def get_card_by_id(card_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    card = cursor.fetchone()
    conn.close()
    return card


async def get_all_cards():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards ORDER BY id")
    cards = cursor.fetchall()
    conn.close()
    return cards


async def get_cards_by_category(category):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cards WHERE category = ?", (category,))
    cards = cursor.fetchall()
    conn.close()
    return cards


async def get_all_categories():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM cards WHERE category IS NOT NULL AND category != ''")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories


async def get_all_artists():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT artist FROM cards ORDER BY artist")
    artists = [row[0] for row in cursor.fetchall()]
    conn.close()
    return artists


async def add_card_to_collection(user_id, card_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_cards (user_id, card_id, count) VALUES (?, ?, 1) "
                   "ON CONFLICT(user_id, card_id) DO UPDATE SET count = count + 1",
                   (user_id, card_id))
    conn.commit()
    conn.close()


async def get_user_collection(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT uc.card_id, uc.count, c.name, c.artist, c.rarity, c.filename, c.category
                      FROM user_cards uc
                      JOIN cards c ON uc.card_id = c.id
                      WHERE uc.user_id = ?
                      ORDER BY c.rarity DESC, uc.card_id''', (user_id,))
    collection = cursor.fetchall()
    conn.close()
    return collection


async def get_collection_stats(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(DISTINCT card_id), SUM(count) FROM user_cards WHERE user_id = ?", (user_id,))
    unique, total = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM cards")
    total_in_game = cursor.fetchone()[0]

    cursor.execute('''SELECT c.rarity, COUNT(DISTINCT uc.card_id)
                      FROM user_cards uc
                      JOIN cards c ON uc.card_id = c.id
                      WHERE uc.user_id = ?
                      GROUP BY c.rarity''', (user_id,))
    rarity_stats = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return {
        "unique": unique or 0,
        "total": total or 0,
        "total_in_game": total_in_game,
        "rarity_stats": rarity_stats
    }


async def get_user_by_username(username):
    username = username.strip().lstrip('@').lower()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


async def remove_card_from_collection(user_id, card_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE user_cards SET count = count - 1 WHERE user_id = ? AND card_id = ?",
                   (user_id, card_id))
    cursor.execute("DELETE FROM user_cards WHERE user_id = ? AND card_id = ? AND count <= 0",
                   (user_id, card_id))
    conn.commit()
    conn.close()


async def get_user_card_count(user_id, card_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?",
                   (user_id, card_id))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


async def add_card_to_db(card_id, name, artist, filename, rarity, category, description, season_tag):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO cards (id, name, artist, filename, rarity, category, description, season_tag)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (card_id, name, artist, filename, rarity, category, description, season_tag))
    conn.commit()
    conn.close()


async def delete_card(card_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    cursor.execute("DELETE FROM user_cards WHERE card_id = ?", (card_id,))
    conn.commit()
    conn.close()


async def get_next_card_id():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM cards")
    result = cursor.fetchone()[0]
    conn.close()
    return (result or 0) + 1


async def get_bot_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0")
    active_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
    blocked_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cards")
    total_cards = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(count) FROM user_cards")
    total_collected = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'completed'")
    completed_trades = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'pending'")
    pending_trades = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(coins) FROM users")
    total_coins = cursor.fetchone()[0] or 0

    conn.close()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "blocked_users": blocked_users,
        "total_cards": total_cards,
        "total_collected": total_collected,
        "completed_trades": completed_trades,
        "pending_trades": pending_trades,
        "total_coins": total_coins
    }


async def get_top_collectors(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT u.user_id, u.username, COUNT(DISTINCT uc.card_id) as unique_cards
                      FROM users u
                      LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                      WHERE u.is_blocked = 0
                      GROUP BY u.user_id
                      ORDER BY unique_cards DESC
                      LIMIT ?''', (limit,))
    result = cursor.fetchall()
    conn.close()
    return result


async def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY registered_at DESC")
    users = cursor.fetchall()
    conn.close()
    return users


async def block_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


async def unblock_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


async def is_user_blocked(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_blocked FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else False


async def save_broadcast(admin_id, broadcast_type, content, sent_count):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO broadcasts (admin_id, type, content, sent_count) VALUES (?, ?, ?, ?)",
                   (admin_id, broadcast_type, content, sent_count))
    conn.commit()
    conn.close()


async def create_promo_code(code, reward_type, reward_value, max_uses, created_by, specific_card_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''INSERT INTO promo_codes (code, reward_type, reward_value, max_uses, created_by, specific_card_id)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                       (code, reward_type, reward_value, max_uses, created_by, specific_card_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


async def get_promo_code(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promo_codes WHERE code = ?", (code,))
    result = cursor.fetchone()
    conn.close()
    return result


async def use_promo_code(code, user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM promo_codes WHERE code = ? AND is_active = 1", (code,))
    promo = cursor.fetchone()

    if not promo:
        conn.close()
        return False, "Промокод не найден или деактивирован", None, 0, None

    promo_code, reward_type, reward_value, max_uses, current_uses, _, _, is_active, specific_card_id = promo

    if current_uses >= max_uses:
        conn.close()
        return False, "Промокод уже использован максимальное количество раз", None, 0, None

    cursor.execute("SELECT user_id FROM promo_uses WHERE user_id = ? AND code = ?", (user_id, code))
    if cursor.fetchone():
        conn.close()
        return False, "Ты уже использовал этот промокод", None, 0, None

    cursor.execute("UPDATE promo_codes SET current_uses = current_uses + 1 WHERE code = ?", (code,))
    cursor.execute("INSERT INTO promo_uses (user_id, code) VALUES (?, ?)", (user_id, code))
    conn.commit()
    conn.close()

    return True, "Промокод активирован!", reward_type, reward_value, specific_card_id


async def get_all_promo_codes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
    promos = cursor.fetchall()
    conn.close()
    return promos


async def deactivate_promo_code(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE promo_codes SET is_active = 0 WHERE code = ?", (code,))
    conn.commit()
    conn.close()


async def activate_promo_code(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE promo_codes SET is_active = 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()


async def delete_promo_code(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM promo_codes WHERE code = ?", (code,))
    cursor.execute("DELETE FROM promo_uses WHERE code = ?", (code,))
    conn.commit()
    conn.close()


async def get_promo_specific_card(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT specific_card_id FROM promo_codes WHERE code = ?", (code,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


async def check_cooldown(user_id, hours):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_card_time, cooldown_reduction_minutes FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return True, 0

    last_time_str = result[0]
    reduction_minutes = result[1] or 0

    if not last_time_str or not isinstance(last_time_str, str):
        return True, 0

    try:
        last_time = datetime.fromisoformat(last_time_str)
    except (ValueError, TypeError):
        return True, 0

    cooldown = timedelta(hours=hours) - timedelta(minutes=reduction_minutes)
    elapsed = datetime.now() - last_time

    if elapsed >= cooldown:
        return True, 0
    else:
        remaining = cooldown - elapsed
        return False, remaining.total_seconds()


async def get_user_achievements(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT achievement_key FROM achievements WHERE user_id = ?", (user_id,))
    achievements = cursor.fetchall()
    conn.close()
    return achievements


async def check_and_award_achievements(user_id):
    from config import ACHIEVEMENTS
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(DISTINCT card_id) FROM user_cards WHERE user_id = ?", (user_id,))
    unique_cards = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(count) FROM user_cards WHERE user_id = ?", (user_id,))
    total_cards = cursor.fetchone()[0] or 0

    cursor.execute("SELECT current_streak FROM users WHERE user_id = ?", (user_id,))
    streak = cursor.fetchone()[0] or 0

    cursor.execute("SELECT trades_completed FROM users WHERE user_id = ?", (user_id,))
    trades = cursor.fetchone()[0] or 0

    new_achievements = []

    achievements_to_check = {
        "first_card": unique_cards >= 1,
        "collector_10": unique_cards >= 10,
        "collector_50": unique_cards >= 50,
        "collector_100": unique_cards >= 100,
        "cards_10": total_cards >= 10,
        "cards_100": total_cards >= 100,
        "streak_7": streak >= 7,
        "streak_30": streak >= 30,
        "trader_1": trades >= 1,
        "trader_10": trades >= 10
    }

    for key, condition in achievements_to_check.items():
        if condition and key in ACHIEVEMENTS:
            cursor.execute("SELECT achievement_key FROM achievements WHERE user_id = ? AND achievement_key = ?",
                           (user_id, key))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO achievements (user_id, achievement_key) VALUES (?, ?)",
                               (user_id, key))
                new_achievements.append(ACHIEVEMENTS[key])

    conn.commit()
    conn.close()

    return new_achievements


async def get_streak_info(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_streak, best_streak, last_daily FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return {"current": 0, "best": 0, "status": "Не начинал"}

    current, best, last_daily = result

    if last_daily:
        last_date = datetime.strptime(last_daily, "%Y-%m-%d").date()
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        if last_date == today:
            status = "Бонус получен сегодня"
        elif last_date == yesterday:
            status = "Серия продолжается"
        else:
            status = "Серия прервана"
            current = 0
    else:
        status = "Не начинал"

    return {"current": current, "best": best, "status": status}


async def update_streak(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT current_streak, best_streak, last_daily FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return 1, 1, datetime.now().date()

    current, best, last_daily = result
    today = datetime.now().date()

    if last_daily:
        last_date = datetime.strptime(last_daily, "%Y-%m-%d").date()
        if last_date == today:
            conn.close()
            return current, best, today
        elif last_date == today - timedelta(days=1):
            current += 1
        else:
            current = 1
    else:
        current = 1

    best = max(best, current)

    cursor.execute("UPDATE users SET current_streak = ?, best_streak = ?, last_daily = ? WHERE user_id = ?",
                   (current, best, today.isoformat(), user_id))
    conn.commit()
    conn.close()

    return current, best, today


async def get_leaderboard_by_cards(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT u.user_id, u.username, COUNT(DISTINCT uc.card_id) as unique_cards
                      FROM users u
                      LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                      WHERE u.is_blocked = 0
                      GROUP BY u.user_id
                      ORDER BY unique_cards DESC
                      LIMIT ?''', (limit,))
    result = cursor.fetchall()
    conn.close()
    return result


async def get_leaderboard_by_coins(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, coins FROM users WHERE is_blocked = 0 ORDER BY coins DESC LIMIT ?",
                   (limit,))
    result = cursor.fetchall()
    conn.close()
    return result


async def get_leaderboard_by_streak(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, current_streak, best_streak FROM users WHERE is_blocked = 0 ORDER BY current_streak DESC LIMIT ?",
        (limit,))
    result = cursor.fetchall()
    conn.close()
    return result


async def get_user_rank(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT COUNT(*) + 1 FROM (
                      SELECT COUNT(DISTINCT uc.card_id) as unique_cards
                      FROM users u
                      LEFT JOIN user_cards uc ON u.user_id = uc.user_id
                      WHERE u.is_blocked = 0
                      GROUP BY u.user_id
                      HAVING unique_cards > (
                          SELECT COUNT(DISTINCT uc2.card_id)
                          FROM user_cards uc2
                          WHERE uc2.user_id = ?
                      )
                  )''', (user_id,))
    rank = cursor.fetchone()[0]
    conn.close()
    return rank


async def get_daily_tasks(user_id):
    from config import DAILY_TASKS
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().date().isoformat()

    tasks = []
    for task_key, task_data in DAILY_TASKS.items():
        cursor.execute("SELECT progress, completed FROM daily_tasks WHERE user_id = ? AND task_key = ? AND date = ?",
                       (user_id, task_key, today))
        result = cursor.fetchone()

        if result:
            progress, completed = result
        else:
            progress = 0
            completed = 0

        tasks.append({
            "key": task_key,
            "name": task_data["name"],
            "description": task_data["description"],
            "target": task_data["target"],
            "reward": task_data["reward"],
            "progress": progress,
            "completed": completed
        })

    conn.close()
    return tasks


async def update_task_progress(user_id, task_type):
    from config import DAILY_TASKS
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().date().isoformat()
    completed_tasks = []

    for task_key, task_data in DAILY_TASKS.items():
        if task_data.get("type") != task_type:
            continue

        cursor.execute("SELECT progress, completed FROM daily_tasks WHERE user_id = ? AND task_key = ? AND date = ?",
                       (user_id, task_key, today))
        result = cursor.fetchone()

        if result:
            progress, completed = result
            if completed:
                continue
            progress += 1
        else:
            progress = 1
            completed = 0
            cursor.execute('''INSERT INTO daily_tasks (user_id, task_key, progress, completed, date)
                             VALUES (?, ?, ?, ?, ?)''',
                           (user_id, task_key, progress, completed, today))

        target = task_data["target"]

        if progress >= target and not completed:
            completed = 1
            cursor.execute("UPDATE daily_tasks SET completed = 1 WHERE user_id = ? AND task_key = ? AND date = ?",
                           (user_id, task_key, today))
            cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?",
                           (task_data["reward"], user_id))
            completed_tasks.append(task_data)
        else:
            cursor.execute("UPDATE daily_tasks SET progress = ? WHERE user_id = ? AND task_key = ? AND date = ?",
                           (progress, user_id, task_key, today))

    conn.commit()
    conn.close()

    return completed_tasks


async def claim_task_reward(user_id, task_key):
    from config import DAILY_TASKS
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().date().isoformat()

    cursor.execute("SELECT progress, completed FROM daily_tasks WHERE user_id = ? AND task_key = ? AND date = ?",
                   (user_id, task_key, today))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return False, 0, "Задание не найдено"

    progress, completed = result

    if completed:
        conn.close()
        return False, 0, "Награда уже получена"

    task_data = DAILY_TASKS.get(task_key)
    if not task_data:
        conn.close()
        return False, 0, "Задание не найдено"

    if progress < task_data["target"]:
        conn.close()
        return False, 0, f"Задание не выполнено. Прогресс: {progress}/{task_data['target']}"

    cursor.execute("UPDATE daily_tasks SET completed = 1 WHERE user_id = ? AND task_key = ? AND date = ?",
                   (user_id, task_key, today))
    cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?",
                   (task_data["reward"], user_id))

    conn.commit()
    conn.close()

    return True, task_data["reward"], "Награда получена!"


async def get_tasks_completed_count(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.now().date().isoformat()
    cursor.execute("SELECT COUNT(*) FROM daily_tasks WHERE user_id = ? AND date = ? AND completed = 1",
                   (user_id, today))
    count = cursor.fetchone()[0]
    conn.close()
    return count


async def create_trade_offer(from_user, to_user, from_card, to_card):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?",
                   (from_user, from_card))
    result = cursor.fetchone()
    if not result or result[0] <= 0:
        conn.close()
        return None, "У тебя нет этой карточки!"

    cursor.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?",
                   (to_user, to_card))
    result = cursor.fetchone()
    if not result or result[0] <= 0:
        conn.close()
        return None, "У этого игрока нет такой карточки!"

    expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

    cursor.execute('''INSERT INTO trades (from_user, to_user, from_card, to_card, expires_at)
                     VALUES (?, ?, ?, ?, ?)''',
                   (from_user, to_user, from_card, to_card, expires_at))
    offer_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return offer_id, None


async def get_trade_offers_for_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE to_user = ? AND status = 'pending'", (user_id,))
    offers = cursor.fetchall()
    conn.close()
    return offers


async def get_trade_offers_from_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE from_user = ? AND status = 'pending'", (user_id,))
    offers = cursor.fetchall()
    conn.close()
    return offers


async def accept_trade_offer(offer_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM trades WHERE id = ? AND to_user = ? AND status = 'pending'",
                   (offer_id, user_id))
    offer = cursor.fetchone()

    if not offer:
        conn.close()
        return False, "Предложение не найдено"

    offer_id_db, from_user, to_user, from_card, to_card, status, created_at, expires_at = offer

    cursor.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?",
                   (from_user, from_card))
    from_result = cursor.fetchone()
    if not from_result or from_result[0] <= 0:
        cursor.execute("UPDATE trades SET status = 'cancelled' WHERE id = ?", (offer_id,))
        conn.commit()
        conn.close()
        return False, "У игрока больше нет этой карточки!"

    cursor.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?",
                   (to_user, to_card))
    to_result = cursor.fetchone()
    if not to_result or to_result[0] <= 0:
        cursor.execute("UPDATE trades SET status = 'cancelled' WHERE id = ?", (offer_id,))
        conn.commit()
        conn.close()
        return False, "У тебя больше нет этой карточки!"

    cursor.execute("UPDATE user_cards SET user_id = ? WHERE user_id = ? AND card_id = ?",
                   (to_user, from_user, from_card))
    cursor.execute("UPDATE user_cards SET user_id = ? WHERE user_id = ? AND card_id = ?",
                   (from_user, to_user, to_card))

    cursor.execute("UPDATE trades SET status = 'completed' WHERE id = ?", (offer_id,))
    cursor.execute("UPDATE users SET trades_completed = trades_completed + 1 WHERE user_id IN (?, ?)",
                   (from_user, to_user))

    conn.commit()
    conn.close()

    return True, "Обмен завершён!"


async def decline_trade_offer(offer_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE trades SET status = 'declined' WHERE id = ? AND to_user = ?",
                   (offer_id, user_id))
    conn.commit()
    conn.close()
    return True, "Предложение отклонено"


async def cancel_trade_offer(offer_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE trades SET status = 'cancelled' WHERE id = ? AND from_user = ?",
                   (offer_id, user_id))
    conn.commit()
    conn.close()
    return True, "Предложение отменено"


async def get_trade_offer(offer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE id = ?", (offer_id,))
    offer = cursor.fetchone()
    conn.close()
    return offer


async def get_user_items(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT item_key, quantity FROM user_items WHERE user_id = ? AND quantity > 0",
                   (user_id,))
    items = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return items


async def add_item(user_id, item_key, quantity=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO user_items (user_id, item_key, quantity)
                     VALUES (?, ?, ?)
                     ON CONFLICT(user_id, item_key)
                     DO UPDATE SET quantity = quantity + ?''',
                   (user_id, item_key, quantity, quantity))
    conn.commit()
    conn.close()


async def remove_item(user_id, item_key, quantity=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE user_items SET quantity = quantity - ? WHERE user_id = ? AND item_key = ?",
                   (quantity, user_id, item_key))
    cursor.execute("DELETE FROM user_items WHERE user_id = ? AND item_key = ? AND quantity <= 0",
                   (user_id, item_key))
    conn.commit()
    conn.close()


async def buy_item(user_id, item_key, price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user or user[0] < price:
        conn.close()
        return False, "Недостаточно монет!"
    cursor.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (price, user_id))
    conn.commit()
    conn.close()
    return True, None


async def open_pack(user_id, pack_config):
    from config import RARITIES
    cards_received = []

    # Универсальная обработка ключей
    min_cards = pack_config.get("min_cards") or pack_config.get("cards_min") or pack_config.get("min") or 1
    max_cards = pack_config.get("max_cards") or pack_config.get("cards_max") or pack_config.get("max") or 3
    max_rarity = pack_config.get("max_rarity", "rare")

    num_cards = random.randint(min_cards, max_cards)

    rarity_order = ["common", "rare", "epic", "legendary", "secret", "mythical"]
    max_rarity_index = rarity_order.index(max_rarity) if max_rarity in rarity_order else 1
    allowed_rarities = rarity_order[:max_rarity_index + 1]

    for _ in range(num_cards):
        rarity = random.choices(allowed_rarities,
                                weights=[RARITIES[r]["chance"] for r in allowed_rarities],
                                k=1)[0]
        card = await get_random_card_by_rarity(rarity)
        if card:
            await add_card_to_collection(user_id, card[0])
            cards_received.append(card)

    return cards_received


async def open_case(user_id, case_key):
    from config import CASES, SHOP_ITEMS
    case = CASES.get(case_key)
    if not case:
        return None, "Кейс не найден!"

    cards_received = []
    items_received = []

    # Универсальная обработка ключей
    min_cards = case.get("min_cards") or case.get("cards_min") or case.get("min") or 1
    max_cards = case.get("max_cards") or case.get("cards_max") or case.get("max") or 3

    num_cards = random.randint(min_cards, max_cards)

    for _ in range(num_cards):
        rarity = random.choices(
            ["common", "rare", "epic", "legendary", "secret"],
            weights=[50, 30, 15, 4.9, 0.1],
            k=1
        )[0]
        card = await get_random_card_by_rarity(rarity)
        if card:
            await add_card_to_collection(user_id, card[0])
            cards_received.append(card)

    for item_key, chance in case.get("bonus_items", {}).items():
        if random.random() * 100 < chance:
            await add_item(user_id, item_key, 1)
            items_received.append(item_key)

    return {"cards": cards_received, "items": items_received}, None


async def use_skip(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT quantity FROM user_items WHERE user_id = ? AND item_key = 'skip'",
                   (user_id,))
    result = cursor.fetchone()

    if not result or result[0] <= 0:
        conn.close()
        return False, "У тебя нет пропусков!"

    cursor.execute("UPDATE user_items SET quantity = quantity - 1 WHERE user_id = ? AND item_key = 'skip'",
                   (user_id,))
    cursor.execute("DELETE FROM user_items WHERE user_id = ? AND item_key = 'skip' AND quantity <= 0",
                   (user_id,))
    cursor.execute("UPDATE users SET last_card_time = ? WHERE user_id = ?",
                   ((datetime.now() - timedelta(hours=3)).isoformat(), user_id))

    conn.commit()
    conn.close()

    return True, "Пропуск использован!"


async def get_extra_claims(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT extra_claims FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


async def use_extra_claim(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET extra_claims = extra_claims - 1 WHERE user_id = ? AND extra_claims > 0",
                   (user_id,))
    conn.commit()
    conn.close()


async def get_effective_cooldown_minutes(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT cooldown_reduction_minutes FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    reduction = result[0] if result else 0
    return max(0, 180 - reduction)


async def get_item_quantity(user_id, item_key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT quantity FROM user_items WHERE user_id = ? AND item_key = ?",
                   (user_id, item_key))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


async def record_purchase(user_id, item_key, price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO purchases (user_id, item_key, price) VALUES (?, ?, ?)",
                   (user_id, item_key, price))
    conn.commit()
    conn.close()


async def create_auction(seller_id, card_id, start_price, duration_hours):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT count FROM user_cards WHERE user_id = ? AND card_id = ?",
                   (seller_id, card_id))
    result = cursor.fetchone()
    if not result or result[0] <= 0:
        conn.close()
        return None, "У тебя нет этой карточки!"

    end_time = (datetime.now() + timedelta(hours=duration_hours)).isoformat()

    cursor.execute('''INSERT INTO auctions (card_id, seller_id, start_price, end_time)
                     VALUES (?, ?, ?, ?)''',
                   (card_id, seller_id, start_price, end_time))
    auction_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return auction_id, None


async def get_active_auctions(limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT a.id, a.card_id, a.seller_id, a.start_price, a.current_bid, 
                             a.current_bidder_id, a.end_time, a.status,
                             u.username, c.name, c.rarity, c.artist
                      FROM auctions a
                      JOIN users u ON a.seller_id = u.user_id
                      JOIN cards c ON a.card_id = c.id
                      WHERE a.status = 'active'
                      ORDER BY a.end_time ASC
                      LIMIT ?''', (limit,))
    auctions = cursor.fetchall()
    conn.close()
    return auctions


async def place_bid(auction_id, bidder_id, amount):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM auctions WHERE id = ? AND status = 'active'", (auction_id,))
    auction = cursor.fetchone()

    if not auction:
        conn.close()
        return False, "Аукцион не найден или завершён"

    aid, card_id, seller_id, start_price, current_bid, current_bidder_id, end_time, status = auction

    if seller_id == bidder_id:
        conn.close()
        return False, "Нельзя ставить ставку на свой лот!"

    min_bid = max(start_price, current_bid) + 50

    if amount < min_bid:
        conn.close()
        return False, f"Минимальная ставка: {min_bid} монет"

    cursor.execute("SELECT coins FROM users WHERE user_id = ?", (bidder_id,))
    bidder = cursor.fetchone()
    if not bidder or bidder[0] < amount:
        conn.close()
        return False, "Недостаточно монет!"

    cursor.execute("UPDATE auctions SET current_bid = ?, current_bidder_id = ? WHERE id = ?",
                   (amount, bidder_id, auction_id))

    conn.commit()
    conn.close()

    return True, f"Ставка {amount} монет принята!"


async def finalize_auction(auction_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM auctions WHERE id = ? AND status = 'active'", (auction_id,))
    auction = cursor.fetchone()

    if not auction:
        conn.close()
        return

    aid, card_id, seller_id, start_price, current_bid, current_bidder_id, end_time, status = auction

    if current_bidder_id:
        cursor.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?",
                       (current_bid, current_bidder_id))

        fee = int(current_bid * 0.10)
        seller_receives = current_bid - fee
        cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?",
                       (seller_receives, seller_id))

        cursor.execute("UPDATE user_cards SET user_id = ? WHERE user_id = ? AND card_id = ?",
                       (current_bidder_id, seller_id, card_id))

    cursor.execute("UPDATE auctions SET status = 'completed' WHERE id = ?", (auction_id,))

    conn.commit()
    conn.close()


async def get_user_auctions(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT a.id, a.card_id, a.start_price, a.current_bid, a.end_time, a.status,
                             c.name, c.rarity
                      FROM auctions a
                      JOIN cards c ON a.card_id = c.id
                      WHERE a.seller_id = ?
                      ORDER BY a.end_time DESC''', (user_id,))
    auctions = cursor.fetchall()
    conn.close()
    return auctions


async def get_auction(auction_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auctions WHERE id = ?", (auction_id,))
    auction = cursor.fetchone()
    conn.close()
    return auction


async def create_listing(seller_id, card_id, price):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ? AND card_id = ?",
                       (seller_id, card_id))
        count = cursor.fetchone()[0]
        if count <= 0:
            conn.close()
            return None, "У тебя нет такой карточки!"

        cursor.execute('''INSERT INTO listings (card_id, seller_id, price, created_at)
                         VALUES (?, ?, ?, ?)''',
                       (card_id, seller_id, price, datetime.now().isoformat()))
        listing_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return listing_id, None
    except Exception as e:
        conn.close()
        return None, f"Ошибка: {e}"


async def get_active_listings(limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT l.id, l.card_id, l.seller_id, l.price, l.created_at, l.status,
                             u.username, c.name, c.rarity, c.artist
                      FROM listings l
                      JOIN users u ON l.seller_id = u.user_id
                      JOIN cards c ON l.card_id = c.id
                      WHERE l.status = 'active'
                      ORDER BY l.created_at DESC
                      LIMIT ?''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return results


async def get_user_listings(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT l.id, l.card_id, l.price, l.created_at, l.status,
                             c.name, c.rarity
                      FROM listings l
                      JOIN cards c ON l.card_id = c.id
                      WHERE l.seller_id = ?
                      ORDER BY l.created_at DESC''', (user_id,))
    results = cursor.fetchall()
    conn.close()
    return results


async def get_listing(listing_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT l.id, l.card_id, l.seller_id, l.price, l.created_at, l.status,
                             u.username, c.name, c.rarity, c.artist
                      FROM listings l
                      JOIN users u ON l.seller_id = u.user_id
                      JOIN cards c ON l.card_id = c.id
                      WHERE l.id = ?''', (listing_id,))
    result = cursor.fetchone()
    conn.close()
    return result


async def buy_listing(listing_id, buyer_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''SELECT l.id, l.card_id, l.seller_id, l.price, l.status
                         FROM listings l WHERE l.id = ? AND l.status = 'active' ''', (listing_id,))
        listing = cursor.fetchone()
        if not listing:
            conn.close()
            return False, "Объявление не найдено или уже продано"

        lid, card_id, seller_id, price, status = listing

        if seller_id == buyer_id:
            conn.close()
            return False, "Нельзя купить свою карточку!"

        cursor.execute("SELECT coins FROM users WHERE user_id = ?", (buyer_id,))
        buyer = cursor.fetchone()
        if not buyer or buyer[0] < price:
            conn.close()
            return False, "Недостаточно монет!"

        cursor.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ? AND card_id = ?",
                       (seller_id, card_id))
        count = cursor.fetchone()[0]
        if count <= 0:
            conn.close()
            return False, "У продавца больше нет этой карточки!"

        cursor.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (price, buyer_id))

        fee = int(price * 0.10)
        seller_receives = price - fee
        cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?",
                       (seller_receives, seller_id))

        cursor.execute("UPDATE user_cards SET user_id = ? WHERE user_id = ? AND card_id = ?",
                       (buyer_id, seller_id, card_id))

        cursor.execute("UPDATE listings SET status = 'sold', sold_at = ? WHERE id = ?",
                       (datetime.now().isoformat(), listing_id))

        conn.commit()
        conn.close()
        return True, f"Покупка успешна! Карточка добавлена в твою коллекцию.\nКомиссия: {fee} монет\nПродавец получил: {seller_receives} монет"
    except Exception as e:
        conn.close()
        return False, f"Ошибка: {e}"


async def cancel_listing(listing_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT seller_id FROM listings WHERE id = ? AND status = 'active'",
                   (listing_id,))
    listing = cursor.fetchone()
    if not listing:
        conn.close()
        return False, "Объявление не найдено"
    if listing[0] != user_id:
        conn.close()
        return False, "Это не твоё объявление!"
    cursor.execute("UPDATE listings SET status = 'cancelled' WHERE id = ?", (listing_id,))
    conn.commit()
    conn.close()
    return True, "Объявление отменено"