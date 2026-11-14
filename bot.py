import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import FSInputFile, BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timedelta
import random
import os
import string
import json
import shutil
import sqlite3
import time
from config import (
    BOT_TOKEN, ADMIN_IDS, CARD_COOLDOWN_HOURS, START_COINS, DAILY_COINS,
    RARITIES, CARDS_FOLDER, ACHIEVEMENTS, STREAK_REWARDS, DAILY_TASKS,
    SHOP_ITEMS, CASES, REFERRAL_BONUS_INVITEE, REFERRAL_BONUS_INVITER,
    ACTIVE_SEASON, SEASONAL_DROP_CHANCE,
    AUCTION_DURATION_HOURS, AUCTION_MIN_BID_INCREMENT, AUCTION_FEE_PERCENT,
    PREMIUM_PRICE, PREMIUM_PRICE_MERCHANT, PREMIUM_DURATION, PREMIUM_BENEFITS,
    EXPEDITION_COOLDOWN_HOURS, EXPEDITION_COOLDOWN_PREMIUM_HOURS, EXPEDITION_COOLDOWN_ADMIN_HOURS,
    EXPEDITION_CHANCES, TREASURE_REWARDS, CASE_TYPES_FOR_TREASURE,
    MERCHANT_OFFERS, MERCHANT_DISCOUNT_ITEM_MIN, MERCHANT_DISCOUNT_ITEM_MAX,
    MERCHANT_DISCOUNT_CASE,
    EXPEDITION_ACHIEVEMENTS,
    MARKET_LISTING_LIMIT,
    GIFT_COOLDOWN_HOURS,
    DB_NAME
)
from database import (
    init_db, get_user, create_user, update_coins, update_last_card_time,
    get_user_coins, get_random_card_by_rarity, get_card_by_id,
    get_all_cards, get_cards_by_category, get_all_categories, get_all_artists,
    add_card_to_collection, get_user_collection,
    get_collection_stats, get_user_by_username, remove_card_from_collection,
    get_user_card_count, add_card_to_db, delete_card, get_next_card_id,
    get_bot_stats, get_top_collectors, get_all_users, block_user, unblock_user,
    is_user_blocked, save_broadcast,
    create_promo_code, get_promo_code, use_promo_code, get_all_promo_codes,
    deactivate_promo_code, activate_promo_code, delete_promo_code,
    get_promo_specific_card, check_cooldown,
    get_user_achievements, check_and_award_achievements,
    get_streak_info, update_streak,
    get_leaderboard_by_cards, get_leaderboard_by_coins, get_leaderboard_by_streak,
    get_user_rank,
    get_daily_tasks, update_task_progress, claim_task_reward, get_tasks_completed_count,
    create_trade_offer, get_trade_offers_for_user, get_trade_offers_from_user,
    accept_trade_offer, decline_trade_offer, cancel_trade_offer, get_trade_offer,
    get_user_items, add_item, remove_item, buy_item, open_pack, open_case,
    use_skip, get_extra_claims, use_extra_claim, get_effective_cooldown_minutes,
    get_item_quantity, record_purchase,
    create_auction, get_active_auctions, place_bid, finalize_auction,
    get_user_auctions, get_auction,
    create_listing, get_active_listings, get_user_listings, get_listing,
    buy_listing, cancel_listing,
    get_premium_status, set_premium, is_premium,
    get_expedition_info, update_expedition, get_expedition_cooldown_hours,
    check_expedition_cooldown, check_expedition_achievements,
    get_active_listings_count, can_create_listing,
    get_last_gift_time, update_last_gift_time, check_gift_cooldown
)
from keyboards import (
    main_menu_keyboard, admin_main_keyboard, admin_stats_keyboard,
    admin_users_keyboard, admin_cards_keyboard, admin_broadcast_keyboard,
    admin_promo_keyboard, promo_list_keyboard, promo_manage_keyboard,
    category_filter_keyboard, back_to_menu_keyboard, back_to_admin_keyboard,
    leaderboard_keyboard, streak_info_keyboard,
    daily_tasks_keyboard, trades_menu_keyboard, trade_create_keyboard,
    trade_offer_keyboard,
    shop_main_keyboard, shop_items_keyboard, shop_packs_keyboard, shop_cases_keyboard,
    buy_item_keyboard, buy_pack_keyboard, buy_case_keyboard, inventory_keyboard,
    collection_view_keyboard, collection_start_keyboard,
    market_main_keyboard, market_sell_keyboard, market_listing_keyboard,
    expedition_keyboard, expedition_result_keyboard, expedition_stats_keyboard,
    merchant_keyboard,
    premium_menu_keyboard, premium_buy_keyboard, premium_benefits_keyboard,
    gift_menu_keyboard, gift_create_keyboard, gift_send_keyboard, gift_confirm_keyboard,
    admin_private_msg_input_keyboard
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
trade_sessions = {}


class AdminStates(StatesGroup):
    waiting_for_card_photo = State()
    waiting_for_card_name = State()
    waiting_for_card_artist = State()
    waiting_for_card_rarity = State()
    waiting_for_card_category = State()
    waiting_for_card_description = State()
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_photo = State()
    waiting_for_broadcast_caption = State()
    waiting_for_user_search = State()
    waiting_for_coins_change = State()
    waiting_for_promo_code_input = State()
    waiting_for_promo_reward_type = State()
    waiting_for_promo_card_choice = State()
    waiting_for_promo_specific_card = State()
    waiting_for_promo_reward_value = State()
    waiting_for_promo_max_uses = State()
    waiting_for_auction_price = State()
    waiting_for_delete_card_id = State()
    waiting_for_private_msg_user = State()
    waiting_for_private_msg_text = State()


class UserStates(StatesGroup):
    waiting_for_promo_code = State()
    waiting_for_trade_username = State()
    waiting_for_trade_user_id = State()
    waiting_for_trade_from_card = State()
    waiting_for_trade_to_card = State()
    waiting_for_bid_amount = State()
    waiting_for_market_price = State()
    waiting_for_gift_coins = State()
    waiting_for_gift_card = State()
    waiting_for_gift_message = State()
    waiting_for_gift_receiver = State()


def is_admin(user_id):
    return user_id in ADMIN_IDS


async def admin_required(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("У тебя нет прав администратора!", show_alert=True)
        return False
    return True


async def message_admin_required(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("У тебя нет прав администратора!")
        return False
    return True


async def safe_send(message, text, **kwargs):
    try:
        return await message.answer(text, **kwargs)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        return await message.answer(text, **kwargs)
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")
        return None


def get_rarity_color(rarity):
    colors = {
        "common": "⚪",
        "rare": "🔵",
        "epic": "🟣",
        "legendary": "🟡",
        "secret": "🔴",
        "mythical": "🟣✨"
    }
    return colors.get(rarity, "⚪")


def get_random_rarity():
    roll = random.uniform(0, 100)
    cumulative = 0
    for rarity, data in RARITIES.items():
        cumulative += data["chance"]
        if roll <= cumulative:
            return rarity
    return "common"


def generate_promo_code(length=8):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def format_seconds(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours} ч. {minutes} мин."
    elif minutes > 0:
        return f"{minutes} мин. {secs} сек."
    else:
        return f"{secs} сек."


async def check_blocked(user_id):
    if await is_user_blocked(user_id):
        return True
    return False


async def send_sticker(message, sticker_key):
    from config import STICKERS
    sticker_id = STICKERS.get(sticker_key)
    if not sticker_id:
        return
    try:
        await message.answer_sticker(sticker=sticker_id)
    except Exception as e:
        logger.warning(f"Не удалось отправить стикер {sticker_key}: {e}")


async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="claim", description="Получить карточку"),
        BotCommand(command="mycards", description="Моя коллекция с номерами"),
        BotCommand(command="card", description="Инфо о карточке"),
        BotCommand(command="collection", description="Моя коллекция"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="wallet", description="Кошелёк"),
        BotCommand(command="daily", description="Ежедневный бонус"),
        BotCommand(command="streak", description="Серия дней"),
        BotCommand(command="tasks", description="Ежедневные задания"),
        BotCommand(command="shop", description="Магазин"),
        BotCommand(command="market", description="Рынок"),
        BotCommand(command="auction", description="Аукционы"),
        BotCommand(command="sell", description="Продать на рынке"),
        BotCommand(command="inventory", description="Инвентарь"),
        BotCommand(command="ref", description="Реферальная ссылка"),
        BotCommand(command="leaderboard", description="Рейтинг"),
        BotCommand(command="achievements", description="Достижения"),
        BotCommand(command="trades", description="Обмены"),
        BotCommand(command="search", description="Поиск"),
        BotCommand(command="view", description="Просмотр коллекции"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="admin", description="Админ-панель"),
        BotCommand(command="expedition", description="Экспедиция"),
        BotCommand(command="premium", description="Premium подписка"),
        BotCommand(command="gift", description="Подарки"),
    ]
    await bot.set_my_commands(commands)
    logging.info("Команды бота установлены")


# ============================================
# ОСНОВНЫЕ ОБРАБОТЧИКИ
# ============================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if await check_blocked(message.from_user.id):
        await message.answer("Ты заблокирован администратором бота.")
        return

    referred_by = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1].replace("ref_", ""))
        except ValueError:
            pass

    user = await get_user(message.from_user.id)

    if message.from_user.username:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET username = ? WHERE user_id = ?",
                       (message.from_user.username, message.from_user.id))
        conn.commit()
        conn.close()

    if not user:
        referral_success = await create_user(message.from_user.id, message.from_user.username, referred_by)
        welcome_text = f"Добро пожаловать в Art Collector Bot!\n"
        welcome_text += f"Тебе начислено {START_COINS} стартовых монет!\n"
        if referral_success and referred_by:
            welcome_text += f"Ты был приглашен другом! Бонус: +{REFERRAL_BONUS_INVITEE} монет\n"
            try:
                await bot.send_message(
                    referred_by,
                    f"Твой друг присоединился! Ты получил +{REFERRAL_BONUS_INVITER} монет!\n"
                    f"Твоя реферальная ссылка: /start ref_{referred_by}"
                )
            except:
                pass
        welcome_text += (
            f"Коллекционируй арты от разных художников!\n"
            f"Получай новую карточку каждые {CARD_COOLDOWN_HOURS} часа\n"
            f"Обменивайся с другими коллекционерами\n"
            f"В магазине есть пакеты, кейсы и предметы!\n"
            f"Рынок и аукционы!\n"
            f"Используй меню ниже:"
        )
        await safe_send(message, welcome_text, reply_markup=main_menu_keyboard())
        await send_sticker(message, "welcome")
    else:
        await safe_send(message,
                        f"С возвращением, {message.from_user.first_name}!\n"
                        f"Используй меню ниже:",
                        reply_markup=main_menu_keyboard())


@dp.message(Command("ref"))
@dp.callback_query(lambda c: c.data == "ref_link")
async def referral_link(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id

    bot_info = await bot.get_me()
    bot_username = bot_info.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

    await safe_send(message,
                    f"Твоя реферальная ссылка\n"
                    f"Пригласи друга и получи +{REFERRAL_BONUS_INVITER} монет!\n"
                    f"Друг получит +{REFERRAL_BONUS_INVITEE} монет в подарок!\n"
                    f"Ссылка:\n{ref_link}\n"
                    f"Просто отправь эту ссылку другу!",
                    reply_markup=back_to_menu_keyboard())


@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not await message_admin_required(message):
        return
    await safe_send(message, "Админ-панель\nВыбери раздел:",
                    reply_markup=admin_main_keyboard())


@dp.callback_query(lambda c: c.data == "admin_main")
async def admin_main(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Админ-панель\nВыбери раздел:",
                                     reply_markup=admin_main_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    stats = await get_bot_stats()
    text = (
        f"Статистика бота\n"
        f"Пользователи:\n"
        f"  - Всего: {stats['total_users']}\n"
        f"  - Активных: {stats['active_users']}\n"
        f"  - Заблокировано: {stats['blocked_users']}\n"
        f"Карточки:\n"
        f"  - Всего в игре: {stats['total_cards']}\n"
        f"  - Собрано игроками: {stats['total_collected']}\n"
        f"Обмены:\n"
        f"  - Завершено: {stats['completed_trades']}\n"
        f"  - Ожидают: {stats['pending_trades']}\n"
        f"Монеты в обороте: {stats['total_coins']:,}"
    )
    await callback.message.edit_text(text, reply_markup=admin_stats_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_top")
async def admin_top(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    top = await get_top_collectors(10)
    text = "Топ-10 коллекционеров\n"
    for i, (user_id, username, unique_cards) in enumerate(top, 1):
        medals = ["🥇", "🥈", "🥉"]
        medal = medals[i - 1] if i <= 3 else f"{i}. "
        username = username or "Без имени"
        text += f"{medal} @{username} - {unique_cards} карточек\n"
    if not top:
        text += "Пока нет данных"
    await callback.message.edit_text(text, reply_markup=admin_stats_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_users")
async def admin_users(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Управление пользователями",
                                     reply_markup=admin_users_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_users_list")
async def admin_users_list(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    users = await get_all_users()
    text = f"Все пользователи ({len(users)})\n"
    for user in users[:20]:
        user_id = user[0]
        username = user[1]
        coins = user[2]
        is_blocked = user[6]
        status = "🔒" if is_blocked else "✅"
        username = username or "Без имени"
        text += f"{status} {user_id} - @{username} ({coins} монет)\n"
    if len(users) > 20:
        text += f"\n...и ещё {len(users) - 20} пользователей"
    await callback.message.edit_text(text, reply_markup=admin_users_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_user_search")
async def admin_user_search(callback: types.CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Введи ID пользователя:")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_user_search)


@dp.message(AdminStates.waiting_for_user_search)
async def process_user_search(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("ID должен быть числом. Попробуй ещё раз:")
        return

    user = await get_user(user_id)
    if not user:
        await message.answer("Пользователь не найден.", reply_markup=back_to_admin_keyboard())
        await state.clear()
        return

    user_id = user[0]
    username = user[1]
    coins = user[2]
    trades = user[5]
    is_blocked = user[6]
    registered = user[7]
    username = username or "Без имени"
    status = "Заблокирован" if is_blocked else "Активен"

    is_ready, seconds_left = await check_cooldown(user_id, CARD_COOLDOWN_HOURS)
    if is_ready:
        cooldown_info = "\nКарточка доступна прямо сейчас"
    else:
        cooldown_info = f"\nСледующая карточка через: {format_seconds(seconds_left)}"

    text = (
        f"Пользователь\n"
        f"ID: {user_id}\n"
        f"Имя: @{username}\n"
        f"Монеты: {coins}\n"
        f"Обменов: {trades}\n"
        f"Статус: {status}"
        f"{cooldown_info}\n"
        f"Регистрация: {registered}"
    )

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="Заблокировать", callback_data=f"admin_block_{user_id}"),
            types.InlineKeyboardButton(text="Разблокировать", callback_data=f"admin_unblock_{user_id}")
        ],
        [
            types.InlineKeyboardButton(text="Сбросить кулдаун", callback_data=f"admin_reset_cd_{user_id}")
        ],
        [
            types.InlineKeyboardButton(text="Назад", callback_data="admin_users")
        ]
    ])

    await message.answer(text, reply_markup=keyboard)
    await state.clear()


@dp.callback_query(lambda c: c.data.startswith("admin_reset_cd_"))
async def admin_reset_cooldown(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    user_id = int(callback.data.replace("admin_reset_cd_", ""))
    past_time = (datetime.now() - timedelta(hours=24)).isoformat()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET last_card_time = ? WHERE user_id = ?", (past_time, user_id))
    conn.commit()
    conn.close()
    await callback.answer(f"Кулдаун сброшен для пользователя {user_id}", show_alert=True)
    await callback.message.edit_text(f"Кулдаун сброшен для пользователя {user_id}!",
                                     reply_markup=back_to_admin_keyboard())


@dp.callback_query(lambda c: c.data.startswith("admin_block_"))
async def admin_block(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    user_id = int(callback.data.replace("admin_block_", ""))
    await block_user(user_id)
    await callback.answer(f"Пользователь {user_id} заблокирован", show_alert=True)
    await callback.message.edit_text(f"Пользователь {user_id} заблокирован", reply_markup=back_to_admin_keyboard())


@dp.callback_query(lambda c: c.data.startswith("admin_unblock_"))
async def admin_unblock(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    user_id = int(callback.data.replace("admin_unblock_", ""))
    await unblock_user(user_id)
    await callback.answer(f"Пользователь {user_id} разблокирован", show_alert=True)
    await callback.message.edit_text(f"Пользователь {user_id} разблокирован", reply_markup=back_to_admin_keyboard())


@dp.callback_query(lambda c: c.data == "admin_cards")
async def admin_cards(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Управление карточками",
                                     reply_markup=admin_cards_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_card_add")
async def admin_card_add(callback: types.CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Отправь фото карточки:")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_card_photo)


@dp.message(AdminStates.waiting_for_card_photo, F.photo)
async def process_card_photo(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = file.file_path
    local_path = f"cards/temp_{message.from_user.id}.jpg"
    await bot.download_file(file_path, local_path)
    await state.update_data(photo_path=local_path)
    await message.answer("Введи название карточки:")
    await state.set_state(AdminStates.waiting_for_card_name)


@dp.message(AdminStates.waiting_for_card_photo)
async def process_card_photo_invalid(message: types.Message):
    await message.answer("Это не фото. Отправь изображение:")


@dp.message(AdminStates.waiting_for_card_name)
async def process_card_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введи имя художника:")
    await state.set_state(AdminStates.waiting_for_card_artist)


@dp.message(AdminStates.waiting_for_card_artist)
async def process_card_artist(message: types.Message, state: FSMContext):
    await state.update_data(artist=message.text)
    await message.answer("Введи редкость (common/rare/epic/legendary/secret/mythical):")
    await state.set_state(AdminStates.waiting_for_card_rarity)


@dp.message(AdminStates.waiting_for_card_rarity)
async def process_card_rarity(message: types.Message, state: FSMContext):
    rarity = message.text.strip().lower()
    if rarity not in RARITIES:
        await message.answer("Недопустимая редкость. Выбери: common, rare, epic, legendary, secret, mythical")
        return
    await state.update_data(rarity=rarity)
    await message.answer("Введи категорию (например: аниме, фэнтези):")
    await state.set_state(AdminStates.waiting_for_card_category)


@dp.message(AdminStates.waiting_for_card_category)
async def process_card_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Введи описание (или отправь '-' чтобы пропустить):")
    await state.set_state(AdminStates.waiting_for_card_description)


@dp.message(AdminStates.waiting_for_card_description)
async def process_card_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get('season_question'):
        season_answer = message.text.strip().lower()
        season_tag = ACTIVE_SEASON if season_answer in ['да', 'yes', 'y', '+'] else None
        description = data.get('description', '')
        card_id = await get_next_card_id()
        filename = f"card_{card_id}.jpg"
        final_path = f"cards/{filename}"
        temp_path = data.get('photo_path')
        if not temp_path or not os.path.exists(temp_path):
            await message.answer("Ошибка: файл фото не найден.", reply_markup=back_to_admin_keyboard())
            await state.clear()
            return
        try:
            shutil.move(temp_path, final_path)
            logger.info(f"Файл сохранён: {final_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения файла: {e}")
            await message.answer(f"Ошибка: {e}", reply_markup=back_to_admin_keyboard())
            await state.clear()
            return
        await add_card_to_db(card_id, data['name'], data['artist'], filename,
                             data['rarity'], data['category'], description, season_tag)
        try:
            with open('cards.json', 'r', encoding='utf-8') as f:
                cards_data = json.load(f)
            cards_data.append({
                "id": card_id, "name": data['name'], "artist": data['artist'],
                "filename": filename, "rarity": data['rarity'],
                "category": data['category'], "description": description,
                "season_tag": season_tag
            })
            with open('cards.json', 'w', encoding='utf-8') as f:
                json.dump(cards_data, f, ensure_ascii=False, indent=2)
            logger.info(f"cards.json обновлён, всего карточек: {len(cards_data)}")
        except Exception as e:
            logger.error(f"Не удалось обновить cards.json: {e}")
        season_marker = " Сезонная!" if season_tag else ""
        await message.answer(
            f"Карточка добавлена{season_marker}!\n"
            f"ID: {card_id}\nНазвание: {data['name']}\n"
            f"Художник: {data['artist']}\nРедкость: {data['rarity']}\n"
            f"Категория: {data['category']}\nФайл: {filename}",
            reply_markup=back_to_admin_keyboard()
        )
        await state.clear()
    else:
        description = message.text if message.text != '-' else ''
        await state.update_data(description=description)
        if ACTIVE_SEASON:
            await message.answer("Это сезонная карточка? (да/нет)")
            await state.update_data(season_question=True)
        else:
            card_id = await get_next_card_id()
            filename = f"card_{card_id}.jpg"
            final_path = f"cards/{filename}"
            temp_path = data.get('photo_path')
            if not temp_path or not os.path.exists(temp_path):
                await message.answer("Ошибка: файл фото не найден.", reply_markup=back_to_admin_keyboard())
                await state.clear()
                return
            try:
                shutil.move(temp_path, final_path)
                logger.info(f"Файл сохранён: {final_path}")
            except Exception as e:
                logger.error(f"Ошибка сохранения файла: {e}")
                await message.answer(f"Ошибка: {e}", reply_markup=back_to_admin_keyboard())
                await state.clear()
                return
            await add_card_to_db(card_id, data['name'], data['artist'], filename,
                                 data['rarity'], data['category'], description, None)
            try:
                with open('cards.json', 'r', encoding='utf-8') as f:
                    cards_data = json.load(f)
                cards_data.append({
                    "id": card_id, "name": data['name'], "artist": data['artist'],
                    "filename": filename, "rarity": data['rarity'],
                    "category": data['category'], "description": description,
                    "season_tag": None
                })
                with open('cards.json', 'w', encoding='utf-8') as f:
                    json.dump(cards_data, f, ensure_ascii=False, indent=2)
                logger.info(f"cards.json обновлён, всего карточек: {len(cards_data)}")
            except Exception as e:
                logger.error(f"Не удалось обновить cards.json: {e}")
            await message.answer(
                f"Карточка добавлена!\nID: {card_id}\nНазвание: {data['name']}\n"
                f"Художник: {data['artist']}\nРедкость: {data['rarity']}\n"
                f"Категория: {data['category']}\nФайл: {filename}",
                reply_markup=back_to_admin_keyboard()
            )
            await state.clear()


@dp.callback_query(lambda c: c.data == "admin_card_list")
async def admin_card_list(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    cards = await get_all_cards()
    text = f"Все карточки ({len(cards)})\n"
    for card in cards:
        card_id = card[0]
        name = card[1]
        artist = card[2]
        category = card[5]
        rarity = card[4]
        color = get_rarity_color(rarity)
        season_marker = " 🎄" if len(card) > 7 and card[7] else ""
        text += f"{color} {card_id}. {name} - {artist} [{category}]{season_marker}\n"
    if not cards:
        text = "Карточек пока нет"
    await callback.message.edit_text(text, reply_markup=admin_cards_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_card_delete")
async def admin_card_delete(callback: types.CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Введи ID карточки для удаления:")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_delete_card_id)


@dp.message(AdminStates.waiting_for_delete_card_id)
async def process_delete_card(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    try:
        card_id = int(message.text)
    except ValueError:
        await message.answer("ID должен быть числом. Попробуй ещё раз:")
        return
    card = await get_card_by_id(card_id)
    if not card:
        await message.answer(f"Карточка с ID {card_id} не найдена!", reply_markup=back_to_admin_keyboard())
        await state.clear()
        return
    await delete_card(card_id)
    card_path = os.path.join(CARDS_FOLDER, card[3])
    if os.path.exists(card_path):
        os.remove(card_path)
        logger.info(f"Файл удалён: {card_path}")
    try:
        with open('cards.json', 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
        cards_data = [c for c in cards_data if c['id'] != card_id]
        with open('cards.json', 'w', encoding='utf-8') as f:
            json.dump(cards_data, f, ensure_ascii=False, indent=2)
        logger.info(f"cards.json обновлён, удалена карточка ID {card_id}")
    except Exception as e:
        logger.error(f"Не удалось обновить cards.json: {e}")
    await message.answer(
        f"Карточка удалена!\n"
        f"ID: {card_id}\n"
        f"Название: {card[1]}\n"
        f"Художник: {card[2]}",
        reply_markup=back_to_admin_keyboard()
    )
    await state.clear()


@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Рассылка\nВыбери тип:",
                                     reply_markup=admin_broadcast_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_broadcast_text")
async def admin_broadcast_text(callback: types.CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Введи текст рассылки:")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_broadcast_text)


@dp.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast_text(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    text = message.text
    users = await get_all_users()
    active_users = [u for u in users if not u[6]]
    sent = 0
    failed = 0
    progress_msg = await message.answer(f"Рассылка... Отправлено: 0/{len(active_users)}")
    for user in active_users:
        try:
            await bot.send_message(user[0], text)
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка рассылки пользователю {user[0]}: {e}")
        if sent % 10 == 0:
            try:
                await progress_msg.edit_text(f"Рассылка... Отправлено: {sent}/{len(active_users)}")
            except:
                pass
    await save_broadcast(message.from_user.id, "text", text, sent)
    await progress_msg.edit_text(
        f"Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}\nВсего активных: {len(active_users)}",
        reply_markup=back_to_admin_keyboard()
    )
    await state.clear()


@dp.callback_query(lambda c: c.data == "admin_broadcast_photo")
async def admin_broadcast_photo(callback: types.CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Отправь фото для рассылки:")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_broadcast_photo)


@dp.message(AdminStates.waiting_for_broadcast_photo, F.photo)
async def process_broadcast_photo(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    photo = message.photo[-1]
    await state.update_data(photo_id=photo.file_id)
    await message.answer("Введи подпись к фото (или '-' чтобы пропустить):")
    await state.set_state(AdminStates.waiting_for_broadcast_caption)


@dp.message(AdminStates.waiting_for_broadcast_caption)
async def process_broadcast_caption(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    data = await state.get_data()
    caption = message.text if message.text != '-' else None
    photo_id = data['photo_id']
    users = await get_all_users()
    active_users = [u for u in users if not u[6]]
    sent = 0
    failed = 0
    progress_msg = await message.answer(f"Рассылка фото... Отправлено: 0/{len(active_users)}")
    for user in active_users:
        try:
            await bot.send_photo(user[0], photo_id, caption=caption)
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка рассылки фото пользователю {user[0]}: {e}")
        if sent % 10 == 0:
            try:
                await progress_msg.edit_text(f"Рассылка фото... Отправлено: {sent}/{len(active_users)}")
            except:
                pass
    await save_broadcast(message.from_user.id, "photo", caption or '', sent)
    await progress_msg.edit_text(
        f"Рассылка фото завершена!\nОтправлено: {sent}\nОшибок: {failed}",
        reply_markup=back_to_admin_keyboard()
    )
    await state.clear()


# ============================================
# АДМИН: ПРОМОКОДЫ (с поддержкой premium_discount)
# ============================================
@dp.callback_query(lambda c: c.data == "admin_promo")
async def admin_promo(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("Управление промокодами\nВыбери действие:",
                                     reply_markup=admin_promo_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "admin_promo_create")
async def admin_promo_create(callback: types.CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await callback.message.edit_text(
        "Создание промокода\n"
        "Введи код промокода (латиница и цифры, например SORRY2024)\n"
        "Или отправь '-' для автоматической генерации:",
        reply_markup=back_to_admin_keyboard()
    )
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_promo_code_input)


@dp.message(AdminStates.waiting_for_promo_code_input)
async def process_promo_code_input(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    code_input = message.text.strip()
    if code_input == '-':
        code = generate_promo_code()
        await state.update_data(promo_code=code)
        await message.answer(
            f"Сгенерирован код: {code}\n"
            "Выбери тип награды:\n"
            "- coins - монеты\n"
            "- card - карточка\n"
            "- premium - Premium подписка (дней)\n"
            "- premium_discount - скидка на Premium (%)"
        )
    else:
        if not code_input.isalnum():
            await message.answer("Код должен содержать только латинские буквы и цифры. Попробуй ещё раз:")
            return
        if len(code_input) < 3:
            await message.answer("Код должен быть минимум 3 символа. Попробуй ещё раз:")
            return
        existing = await get_promo_code(code_input)
        if existing:
            await message.answer("Такой промокод уже существует. Попробуй другой:")
            return
        await state.update_data(promo_code=code_input.upper())
        await message.answer(
            f"Код: {code_input.upper()}\n"
            "Выбери тип награды:\n"
            "- coins - монеты\n"
            "- card - карточка\n"
            "- premium - Premium подписка (дней)\n"
            "- premium_discount - скидка на Premium (%)"
        )
    await state.set_state(AdminStates.waiting_for_promo_reward_type)


@dp.message(AdminStates.waiting_for_promo_reward_type)
async def process_promo_reward_type(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    reward_type = message.text.lower().strip()
    valid_types = ['coins', 'card', 'premium', 'premium_discount']
    if reward_type not in valid_types:
        await message.answer("Недопустимый тип. Выбери: coins, card, premium или premium_discount")
        return
    await state.update_data(reward_type=reward_type)
    if reward_type == 'card':
        await message.answer(
            "Выбери тип карточки:\n"
            "- random - случайная карточка\n"
            "- specific - конкретная карточка (нужен ID)\n"
            "Введи тип:")
        await state.set_state(AdminStates.waiting_for_promo_card_choice)
    elif reward_type == 'premium':
        await message.answer("Введи количество дней Premium (например, 30):")
        await state.set_state(AdminStates.waiting_for_promo_reward_value)
    elif reward_type == 'premium_discount':
        await message.answer("Введи процент скидки (например, 50 = скидка 50%):")
        await state.set_state(AdminStates.waiting_for_promo_reward_value)
    else:
        await message.answer("Введи количество монет (например, 500):")
        await state.set_state(AdminStates.waiting_for_promo_reward_value)


@dp.message(AdminStates.waiting_for_promo_card_choice)
async def process_promo_card_choice(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    choice = message.text.lower().strip()
    if choice not in ['random', 'specific']:
        await message.answer("Выбери: random или specific")
        return
    if choice == 'random':
        await state.update_data(specific_card_id=None)
        await message.answer("Введи значение (для карточки не важно, введи 1):")
        await state.set_state(AdminStates.waiting_for_promo_reward_value)
    else:
        cards = await get_all_cards()
        if not cards:
            await message.answer("В базе нет карточек. Сначала добавь карточки через админку.")
            await state.clear()
            return
        text = "Список карточек:\n"
        for card in cards:
            card_id = card[0]
            name = card[1]
            artist = card[2]
            rarity = card[4]
            color = get_rarity_color(rarity)
            text += f"{color} {card_id}. {name} ({artist})\n"
        text += "\nВведи ID нужной карточки:"
        await message.answer(text)
        await state.set_state(AdminStates.waiting_for_promo_specific_card)


@dp.message(AdminStates.waiting_for_promo_specific_card)
async def process_promo_specific_card(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    try:
        card_id = int(message.text)
    except ValueError:
        await message.answer("ID должен быть числом. Попробуй ещё раз:")
        return
    card = await get_card_by_id(card_id)
    if not card:
        await message.answer(f"Карточка с ID {card_id} не найдена. Попробуй другой ID:")
        return
    await state.update_data(specific_card_id=card_id)
    await message.answer(f"Выбрана карточка: {card[1]} ({card[2]})\nВведи значение (для карточки не важно, введи 1):")
    await state.set_state(AdminStates.waiting_for_promo_reward_value)


@dp.message(AdminStates.waiting_for_promo_reward_value)
async def process_promo_reward_value(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    try:
        reward_value = int(message.text)
        if reward_value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи положительное число")
        return
    # Для premium_discount ограничиваем скидку 1-90%
    data = await state.get_data()
    if data.get('reward_type') == 'premium_discount':
        if reward_value > 90:
            await message.answer("Максимальная скидка 90%. Попробуй ещё раз:")
            return
    await state.update_data(reward_value=reward_value)
    await message.answer("Введи максимальное количество использований (например, 100):")
    await state.set_state(AdminStates.waiting_for_promo_max_uses)


@dp.message(AdminStates.waiting_for_promo_max_uses)
async def process_promo_max_uses(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    try:
        max_uses = int(message.text)
        if max_uses <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи положительное число")
        return
    data = await state.get_data()
    code = data['promo_code']
    reward_type = data['reward_type']
    reward_value = data['reward_value']
    specific_card_id = data.get('specific_card_id')

    success = await create_promo_code(code, reward_type, reward_value, max_uses, message.from_user.id, specific_card_id)

    if success:
        if reward_type == 'coins':
            reward_text = f"{reward_value} монет"
        elif reward_type == 'premium':
            reward_text = f"Premium на {reward_value} дней"
        elif reward_type == 'premium_discount':
            reward_text = f"Скидка {reward_value}% на Premium"
        elif specific_card_id:
            card = await get_card_by_id(specific_card_id)
            reward_text = f"конкретная карточка: {card[1] if card else 'ID ' + str(specific_card_id)}"
        else:
            reward_text = "случайная карточка"
        await message.answer(
            f"Промокод создан!\nКод: {code}\nНаграда: {reward_text}\nЛимит использований: {max_uses}\n"
            "Скопируй код и поделись с пользователями!",
            reply_markup=back_to_admin_keyboard()
        )
    else:
        await message.answer("Ошибка создания промокода. Возможно, такой код уже существует.",
                             reply_markup=back_to_admin_keyboard())
    await state.clear()


@dp.callback_query(lambda c: c.data == "admin_promo_list")
async def admin_promo_list(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    promos = await get_all_promo_codes()
    if not promos:
        await callback.message.edit_text("Промокодов пока нет.", reply_markup=admin_promo_keyboard())
        await callback.answer()
        return
    await callback.message.edit_text("Список промокодов\nНажми на промокод для управления:",
                                     reply_markup=promo_list_keyboard(promos))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("promo_manage_"))
async def promo_manage(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    code = callback.data.replace("promo_manage_", "")
    promo = await get_promo_code(code)
    if not promo:
        await callback.answer("Промокод не найден", show_alert=True)
        return
    promo_code = promo[0]
    reward_type = promo[1]
    reward_value = promo[2]
    max_uses = promo[3]
    current_uses = promo[4]
    is_active = promo[7]
    status = "Активен" if is_active else "Деактивирован"
    if reward_type == 'coins':
        reward_text = f"{reward_value} монет"
    elif reward_type == 'premium':
        reward_text = f"Premium на {reward_value} дней"
    elif reward_type == 'premium_discount':
        reward_text = f"Скидка {reward_value}% на Premium"
    else:
        specific_card_id = await get_promo_specific_card(code)
        if specific_card_id:
            card = await get_card_by_id(specific_card_id)
            reward_text = f"карточка: {card[1] if card else 'ID ' + str(specific_card_id)}"
        else:
            reward_text = "случайная карточка"
    text = f"Промокод: {promo_code}\nНаграда: {reward_text}\nИспользований: {current_uses}/{max_uses}\nСтатус: {status}"
    await callback.message.edit_text(text, reply_markup=promo_manage_keyboard(code, is_active))
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("promo_deactivate_"))
async def promo_deactivate(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    code = callback.data.replace("promo_deactivate_", "")
    await deactivate_promo_code(code)
    await callback.answer(f"Промокод {code} деактивирован", show_alert=True)
    await callback.message.edit_text(f"Промокод {code} деактивирован", reply_markup=back_to_admin_keyboard())


@dp.callback_query(lambda c: c.data.startswith("promo_activate_"))
async def promo_activate_admin(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    code = callback.data.replace("promo_activate_", "")
    await activate_promo_code(code)
    await callback.answer(f"Промокод {code} активирован", show_alert=True)
    await callback.message.edit_text(f"Промокод {code} активирован", reply_markup=back_to_admin_keyboard())


@dp.callback_query(lambda c: c.data.startswith("promo_delete_"))
async def promo_delete(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    code = callback.data.replace("promo_delete_", "")
    await delete_promo_code(code)
    await callback.answer(f"Промокод {code} удалён", show_alert=True)
    await callback.message.edit_text(f"Промокод {code} удалён", reply_markup=back_to_admin_keyboard())


@dp.callback_query(lambda c: c.data == "admin_settings")
async def admin_settings(callback: types.CallbackQuery):
    if not await admin_required(callback):
        return
    text = (
        "⚙️ Настройки бота\n"
        f"📊 Кулдаун карточки: {CARD_COOLDOWN_HOURS} часов\n"
        f"💰 Стартовые монеты: {START_COINS}\n"
        f"🎁 Ежедневный бонус: {DAILY_COINS} монет\n"
        f"⭐ Premium цена: {PREMIUM_PRICE} Stars/мес\n"
        f"🗺️ Кулдаун экспедиции: {EXPEDITION_COOLDOWN_HOURS} часов\n"
        f"🏪 Лимит рынка: {MARKET_LISTING_LIMIT} карточек\n"
        f"🎁 Кулдаун подарков: {GIFT_COOLDOWN_HOURS} часов\n"
        "Эти настройки можно изменить в config.py"
    )
    await callback.message.edit_text(text, reply_markup=back_to_admin_keyboard())
    await callback.answer()


# ============================================
# АДМИН: ЛИЧНЫЕ СООБЩЕНИЯ
# ============================================
@dp.callback_query(lambda c: c.data == "admin_private_msg")
async def admin_private_msg(callback: types.CallbackQuery, state: FSMContext):
    if not await admin_required(callback):
        return
    await callback.message.edit_text("✉️ Личное сообщение пользователю\nВведи ID пользователя:")
    await callback.answer()
    await state.set_state(AdminStates.waiting_for_private_msg_user)


@dp.message(AdminStates.waiting_for_private_msg_user)
async def process_private_msg_user(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("ID должен быть числом. Попробуй ещё раз:")
        return
    user = await get_user(user_id)
    if not user:
        await message.answer("Пользователь не найден. Введи другой ID:")
        return
    await state.update_data(private_msg_user_id=user_id)
    await message.answer(f"Пользователь найден: @{user[1] or 'без username'}\nВведи текст сообщения:")
    await state.set_state(AdminStates.waiting_for_private_msg_text)


@dp.message(AdminStates.waiting_for_private_msg_text)
async def process_private_msg_text(message: types.Message, state: FSMContext):
    if not await message_admin_required(message):
        return
    data = await state.get_data()
    user_id = data.get('private_msg_user_id')
    text = message.text
    try:
        await bot.send_message(user_id, f"📩 Сообщение от администрации:\n{text}")
        await message.answer(f"✅ Сообщение отправлено пользователю {user_id}!", reply_markup=back_to_admin_keyboard())
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}\nВозможно, пользователь заблокировал бота.",
                             reply_markup=back_to_admin_keyboard())
    await state.clear()


# ============================================
# ПОЛЬЗОВАТЕЛЬ: АКТИВАЦИЯ ПРОМОКОДА (с premium_discount)
# ============================================
@dp.callback_query(lambda c: c.data == "promo_activate")
async def promo_activate_user(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Активация промокода\nВведи промокод:")
    await callback.answer()
    await state.set_state(UserStates.waiting_for_promo_code)


@dp.message(UserStates.waiting_for_promo_code)
async def process_promo_code(message: types.Message, state: FSMContext):
    if await check_blocked(message.from_user.id):
        await message.answer("Ты заблокирован.")
        await state.clear()
        return

    code = message.text.strip().upper()
    success, msg, reward_type, reward_value, specific_card_id = await use_promo_code(code, message.from_user.id)

    if not success:
        await message.answer(msg, reply_markup=main_menu_keyboard())
        await state.clear()
        return

    await send_sticker(message, "promo")

    # НОВОЕ: скидка на Premium
    if reward_type == 'premium_discount':
        await state.update_data(premium_discount=reward_value)
        discount_price = int(PREMIUM_PRICE * (100 - reward_value) / 100)
        await message.answer(
            f"✅ Промокод активирован!\n\n"
            f"🎟️ Тип: Скидка на Premium\n"
            f"💎 Размер скидки: {reward_value}%\n\n"
            f"Обычная цена Premium: {PREMIUM_PRICE} Stars\n"
            f"Цена со скидкой: {discount_price} Stars\n\n"
            f"Нажми кнопку ниже, чтобы купить Premium со скидкой:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"💎 Купить Premium за {discount_price} Stars",
                                      callback_data="premium_buy_discounted")],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
            ])
        )
        await state.clear()
        return

    if reward_type == 'coins':
        await update_coins(message.from_user.id, reward_value)
        await message.answer(f"Промокод активирован!\nТебе начислено {reward_value} монет!",
                             reply_markup=main_menu_keyboard())
        await update_task_progress(message.from_user.id, "promo")
    elif reward_type == 'premium':
        await set_premium(message.from_user.id, reward_value)
        await message.answer(f"Промокод активирован!\n⭐ Premium подписка на {reward_value} дней активирована!",
                             reply_markup=main_menu_keyboard())
    elif reward_type == 'card':
        if specific_card_id:
            card = await get_card_by_id(specific_card_id)
        else:
            rarity = get_random_rarity()
            card = await get_random_card_by_rarity(rarity)
        if card:
            await add_card_to_collection(message.from_user.id, card[0])
            rarity_color = get_rarity_color(card[4])
            card_text = f"Промокод активирован!\nТы получил карточку:\n{rarity_color} {card[1]}\n"
            card_text += f"Художник: {card[2]}\nРедкость: {rarity_color} {card[4].capitalize()}\nКатегория: {card[5]}"
            if card[6]:
                card_text += f"\n{card[6]}"
            card_path = os.path.join(CARDS_FOLDER, card[3])
            if os.path.exists(card_path):
                try:
                    photo = FSInputFile(card_path)
                    await message.answer_photo(photo=photo, caption=card_text, reply_markup=main_menu_keyboard())
                except Exception as e:
                    logger.error(f"Ошибка отправки фото промокода: {e}")
                    await message.answer(card_text, reply_markup=main_menu_keyboard())
            else:
                await message.answer(card_text, reply_markup=main_menu_keyboard())
        else:
            await message.answer(
                f"Промокод активирован!\nНо к сожалению, сейчас нет доступных карточек. Попробуй позже!",
                reply_markup=main_menu_keyboard())
    await state.clear()


@dp.callback_query(lambda c: c.data == "cancel")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Отменено")
    await state.clear()
    await callback.message.edit_text("Действие отменено.", reply_markup=main_menu_keyboard())


# ============================================
# ПОЛЬЗОВАТЕЛЬ: ПОЛУЧЕНИЕ КАРТОЧКИ (исправлено)
# ============================================
@dp.message(Command("claim"))
@dp.callback_query(lambda c: c.data == "claim_card")
async def claim_card(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id

    if await check_blocked(user_id):
        await safe_send(message, "Ты заблокирован администратором.")
        return

    user = await get_user(user_id)
    if not user:
        await create_user(user_id, message.from_user.username)
        user = await get_user(user_id)

    if not is_admin(user_id):
        is_ready, seconds_left = await check_cooldown(user_id, CARD_COOLDOWN_HOURS)
        if not is_ready:
            skip_count = await get_item_quantity(user_id, "skip")
            skip_info = f"\nУ тебя есть Пропусков: {skip_count}\nИспользуй /inventory чтобы применить" if skip_count > 0 else ""
            await safe_send(message,
                            f"Ты недавно получил карточку!\n"
                            f"Следующая через: {format_seconds(seconds_left)}{skip_info}",
                            reply_markup=back_to_menu_keyboard())
            return
    else:
        logger.info(f"Админ {user_id} получает карточку без кулдауна")

    extra_claims = await get_extra_claims(user_id)
    claims_count = 1 + extra_claims
    has_pack = extra_claims > 0
    all_received_cards = []
    best_rarity_order = ["mythical", "secret", "legendary", "epic", "rare", "common"]
    best_rarity_found = "common"
    last_rarity = "common"

    for claim_num in range(claims_count):
        is_seasonal = False
        if ACTIVE_SEASON and random.random() * 100 < SEASONAL_DROP_CHANCE:
            is_seasonal = True
        rarity = get_random_rarity()
        if is_seasonal:
            card = await get_random_card_by_rarity(rarity, season_only=True)
            if not card:
                card = await get_random_card_by_rarity(rarity, season_only=False)
        else:
            card = await get_random_card_by_rarity(rarity, season_only=False)
        if not card:
            for try_rarity in best_rarity_order:
                card = await get_random_card_by_rarity(try_rarity)
                if card:
                    rarity = try_rarity
                    break
        if not card:
            break
        if has_pack and claim_num > 0:
            existing_ids = [c[0] for c in all_received_cards]
            attempts = 0
            while card[0] in existing_ids and attempts < 10:
                rarity = get_random_rarity()
                card = await get_random_card_by_rarity(rarity)
                attempts += 1
        await add_card_to_collection(user_id, card[0])
        all_received_cards.append(card)
        last_rarity = rarity
        if best_rarity_order.index(rarity) < best_rarity_order.index(best_rarity_found):
            best_rarity_found = rarity

    if not all_received_cards:
        await safe_send(message, "К сожалению, сейчас нет доступных карточек. Попробуй позже!",
                        reply_markup=back_to_menu_keyboard())
        return

    await update_last_card_time(user_id)
    if has_pack:
        await use_extra_claim(user_id)

    completed_tasks = await update_task_progress(user_id, "claim")

    if best_rarity_found == "mythical":
        await send_sticker(message, "mythical_card")
    elif best_rarity_found == "secret":
        await send_sticker(message, "secret_card")
    elif best_rarity_found == "legendary":
        await send_sticker(message, "legendary_card")

    if len(all_received_cards) == 1:
        card = all_received_cards[0]
        rarity = last_rarity
        rarity_color = get_rarity_color(card[4])
        season_marker = " 🎄" if len(card) > 7 and card[7] else ""
        card_text = f"Новая карточка{season_marker}!\n"
        card_text += f"{rarity_color} {card[1]}\n"
        card_text += f"Художник: {card[2]}\n"
        card_text += f"Редкость: {rarity_color} {rarity.capitalize()}\n"
        card_text += f"Категория: {card[5]}\n"
        if card[6]:
            card_text += f"\n{card[6]}"
        card_path = os.path.join(CARDS_FOLDER, card[3])
        if os.path.exists(card_path):
            try:
                photo = FSInputFile(card_path)
                await message.answer_photo(photo=photo, caption=card_text, reply_markup=back_to_menu_keyboard())
            except Exception as e:
                logger.error(f"Ошибка фото: {e}")
                await safe_send(message, card_text, reply_markup=back_to_menu_keyboard())
        else:
            await safe_send(message, card_text, reply_markup=back_to_menu_keyboard())
        bonus = RARITIES[rarity]["multiplier"]
        if await is_premium(user_id):
            bonus *= 2
        if bonus > 1:
            await update_coins(user_id, bonus)
            await safe_send(message, f"\nБонус за редкость: +{bonus} монет!")
    else:
        pack_text = f"Пакет открыт! Получено карточек: {len(all_received_cards)}\n"
        for card in all_received_cards:
            rarity_color = get_rarity_color(card[4])
            pack_text += f"{rarity_color} {card[1]} - {card[2]} [{card[4].capitalize()}]\n"
            bonus = RARITIES[card[4]]["multiplier"]
            if await is_premium(user_id):
                bonus *= 2
            if bonus > 1:
                await update_coins(user_id, bonus)
        await safe_send(message, pack_text, reply_markup=back_to_menu_keyboard())

    if completed_tasks:
        await asyncio.sleep(1)
        for task in completed_tasks:
            await safe_send(message,
                            f"Задание выполнено!\n"
                            f"{task['name']}\n"
                            f"Награда: +{task['reward']} монет\n"
                            f"Забери награду в разделе Задания")

    new_achievements = await check_and_award_achievements(user_id)
    if new_achievements:
        await asyncio.sleep(1)
        for ach in new_achievements:
            await send_sticker(message, "achievement")
            await safe_send(message,
                            f"Новое достижение!\n{ach['name']}\n{ach['description']}\n+{ach['reward']} монет")


# ============================================
# ОСТАЛЬНЫЕ КОМАНДЫ (mycards, card, collection и т.д.)
# ============================================
@dp.message(Command("mycards"))
async def my_cards(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала запусти бота командой /start")
        return
    collection = await get_user_collection(user_id)
    if not collection:
        await message.answer(
            "Твоя коллекция пуста!\n"
            "Используй /claim чтобы получить первую карточку.",
            reply_markup=collection_start_keyboard(False)
        )
        return
    by_rarity = {"mythical": [], "secret": [], "legendary": [], "epic": [], "rare": [], "common": []}
    for card in collection:
        card_id = card[0]
        count = card[1]
        name = card[2]
        artist = card[3]
        rarity = card[4]
        filename = card[5]
        category = card[6]
        if rarity in by_rarity:
            by_rarity[rarity].append((card_id, count, name, artist, category, filename))
    text = "Твоя коллекция (с номерами)\n"
    text += "Используй эти номера для обмена и аукционов!\n"
    total_unique = 0
    for rarity in ["mythical", "secret", "legendary", "epic", "rare", "common"]:
        if by_rarity[rarity]:
            color = get_rarity_color(rarity)
            text += f"{color} {rarity.capitalize()} ({len(by_rarity[rarity])})\n"
            for card_id, count, name, artist, category, filename in by_rarity[rarity]:
                dup = f" x{count}" if count > 1 else ""
                text += f"- Номер {card_id}: {name} - {artist}{dup}\n"
                total_unique += 1
            text += "\n"
    text += f"Всего уникальных: {total_unique}"
    await message.answer(text, reply_markup=collection_start_keyboard(True))


@dp.message(Command("card"))
async def card_info(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Информация о карточке\n"
            "Использование: /card номер\n"
            "Пример: /card 42\n"
            "Чтобы увидеть номера своих карточек: /mycards"
        )
        return
    try:
        card_id = int(args[1])
    except ValueError:
        await message.answer("Номер должен быть числом!")
        return
    card = await get_card_by_id(card_id)
    if not card:
        await message.answer(f"Карточка с номером {card_id} не найдена!")
        return
    card_id_db = card[0]
    name = card[1]
    artist = card[2]
    filename = card[3]
    rarity = card[4]
    category = card[5]
    description = card[6] if len(card) > 6 else None
    color = get_rarity_color(rarity)
    season_marker = " 🎄" if len(card) > 7 and card[7] else ""
    text = (
        f"{color} Карточка номер {card_id_db}{season_marker}\n"
        f"{name}\n"
        f"Художник: {artist}\n"
        f"Редкость: {rarity.capitalize()}\n"
        f"Категория: {category}\n"
    )
    if description:
        text += f"\n{description}"
    card_path = os.path.join(CARDS_FOLDER, filename)
    if os.path.exists(card_path):
        try:
            photo = FSInputFile(card_path)
            await message.answer_photo(photo=photo, caption=text)
        except:
            await message.answer(text)
    else:
        await message.answer(text)


@dp.message(Command("collection"))
@dp.callback_query(lambda c: c.data == "collection")
async def show_collection(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    collection = await get_user_collection(user_id)
    if not collection:
        await safe_send(message,
                        "Коллекция пуста!\nИспользуй /claim",
                        reply_markup=collection_start_keyboard(False))
        return
    by_rarity = {"mythical": [], "secret": [], "legendary": [], "epic": [], "rare": [], "common": []}
    for card in collection:
        card_id = card[0]
        count = card[1]
        name = card[2]
        artist = card[3]
        rarity = card[4]
        filename = card[5]
        category = card[6]
        if rarity in by_rarity:
            by_rarity[rarity].append((card_id, count, name, artist, category, filename))
    collection_text = "Твоя коллекция\n"
    total_unique = 0
    for rarity in ["mythical", "secret", "legendary", "epic", "rare", "common"]:
        if by_rarity[rarity]:
            color = get_rarity_color(rarity)
            collection_text += f"{color} {rarity.capitalize()} ({len(by_rarity[rarity])})\n"
            for card_id, count, name, artist, category, filename in by_rarity[rarity]:
                dup = f" x{count}" if count > 1 else ""
                collection_text += f"- {name} - {artist}{dup}\n"
                total_unique += 1
            collection_text += "\n"
    collection_text += f"Всего уникальных: {total_unique}"
    await safe_send(message, collection_text, reply_markup=collection_start_keyboard(True))


@dp.callback_query(lambda c: c.data == "col_view_0")
async def collection_view_start(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    user_id = callback.from_user.id
    collection = await get_user_collection(user_id)
    if not collection:
        await callback.message.answer("Коллекция пуста!")
        return
    cards_list = []
    for card in collection:
        card_id = card[0]
        count = card[1]
        name = card[2]
        artist = card[3]
        rarity = card[4]
        filename = card[5]
        category = card[6]
        cards_list.append((card_id, count, name, artist, rarity, filename, category))
    await show_collection_card(callback.message, cards_list, 0)


@dp.callback_query(lambda c: c.data.startswith("col_next_") or c.data.startswith("col_prev_"))
async def collection_view_navigate(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    user_id = callback.from_user.id
    collection = await get_user_collection(user_id)
    if not collection:
        await callback.message.answer("Коллекция пуста!")
        return
    cards_list = []
    for card in collection:
        card_id = card[0]
        count = card[1]
        name = card[2]
        artist = card[3]
        rarity = card[4]
        filename = card[5]
        category = card[6]
        cards_list.append((card_id, count, name, artist, rarity, filename, category))
    if callback.data.startswith("col_next_"):
        current_index = int(callback.data.replace("col_next_", ""))
        new_index = min(current_index + 1, len(cards_list) - 1)
    else:
        current_index = int(callback.data.replace("col_prev_", ""))
        new_index = max(current_index - 1, 0)
    await show_collection_card(callback.message, cards_list, new_index)


async def show_collection_card(message, cards_list, index):
    if index < 0 or index >= len(cards_list):
        return
    card_id, count, name, artist, rarity, filename, category = cards_list[index]
    color = get_rarity_color(rarity)
    caption = (
        f"{color} Карточка {index + 1} из {len(cards_list)}\n"
        f"{name}\n"
        f"Художник: {artist}\n"
        f"Редкость: {rarity.capitalize()}\n"
        f"Категория: {category}\n"
    )
    if count > 1:
        caption += f"\nКоличество: x{count}"
    card_path = os.path.join(CARDS_FOLDER, filename)
    keyboard = collection_view_keyboard(cards_list, index)
    if os.path.exists(card_path):
        try:
            photo = FSInputFile(card_path)
            await message.answer_photo(photo=photo, caption=caption, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            await message.answer(caption + "\nФото не найдено", reply_markup=keyboard)
    else:
        await message.answer(caption, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "noop")
async def noop_callback(callback: types.CallbackQuery):
    await callback.answer()


@dp.message(Command("stats"))
@dp.callback_query(lambda c: c.data == "stats")
async def show_stats(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    stats = await get_collection_stats(user_id)
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    completion = (stats["unique"] / stats["total_in_game"] * 100) if stats["total_in_game"] > 0 else 0
    effective_minutes = await get_effective_cooldown_minutes(user_id)
    effective_hours = effective_minutes // 60
    effective_mins = effective_minutes % 60
    coins = user[2]
    trades = user[5]
    stats_text = f"Твоя статистика\n"
    stats_text += f"Уникальных: {stats['unique']} из {stats['total_in_game']}\n"
    stats_text += f"Всего: {stats['total']}\n"
    stats_text += f"Завершение: {completion:.1f}%\n"
    stats_text += f"Монеты: {coins}\n"
    stats_text += f"Обменов: {trades}\n"
    stats_text += f"Кулдаун: {effective_hours} ч. {effective_mins} мин.\n"
    if stats["rarity_stats"]:
        stats_text += "По редкостям:\n"
        for rarity in ["mythical", "secret", "legendary", "epic", "rare", "common"]:
            count = stats["rarity_stats"].get(rarity, 0)
            if count > 0:
                color = get_rarity_color(rarity)
                stats_text += f"{color} {rarity.capitalize()}: {count}\n"
    await safe_send(message, stats_text, reply_markup=back_to_menu_keyboard())


@dp.message(Command("wallet"))
@dp.callback_query(lambda c: c.data == "wallet")
async def show_wallet(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    coins = await get_user_coins(user_id)
    await safe_send(message,
                    f"Твой кошелёк\n"
                    f"Баланс: {coins} монет\n"
                    f"Как получить:\n"
                    f"- /daily (+{DAILY_COINS} + бонус серии)\n"
                    f"- Редкие карточки\n"
                    f"- Успешные обмены\n"
                    f"- Промокоды\n"
                    f"- Достижения\n"
                    f"- Ежедневные задания\n"
                    f"- Аукционы (/auction)\n"
                    f"- Рынок (/market)",
                    reply_markup=back_to_menu_keyboard())


@dp.message(Command("daily"))
@dp.callback_query(lambda c: c.data == "daily_from_streak")
async def cmd_daily(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    if await check_blocked(user_id):
        await message.answer("Ты заблокирован.")
        return
    user = await get_user(user_id)
    if not user:
        await message.answer("Сначала /start")
        return
    today = datetime.now().date()
    daily_claimed_str = user[4]
    last_claimed = datetime.strptime(daily_claimed_str, "%Y-%m-%d").date() if daily_claimed_str else None
    if last_claimed and last_claimed >= today:
        await safe_send(message, "Бонус уже получен сегодня!", reply_markup=back_to_menu_keyboard())
        return
    await send_sticker(message, "daily")
    new_streak, best_streak, _ = await update_streak(user_id)
    streak_bonus = 0
    reward_desc = ""
    if new_streak in STREAK_REWARDS:
        streak_bonus = STREAK_REWARDS[new_streak]["coins"] - DAILY_COINS
        reward_desc = STREAK_REWARDS[new_streak]["description"]
    else:
        available_streaks = sorted([s for s in STREAK_REWARDS.keys() if s <= new_streak], reverse=True)
        if available_streaks:
            closest = available_streaks[0]
            streak_bonus = STREAK_REWARDS[closest]["coins"] - DAILY_COINS
            next_streak = min(s for s in STREAK_REWARDS.keys() if s > new_streak)
            reward_desc = f"{new_streak} дней подряд (ближайший бонус на {next_streak} дней)"
        else:
            reward_desc = f"{new_streak} дней подряд"
    total_reward = DAILY_COINS + streak_bonus
    if await is_premium(user_id):
        total_reward *= 2
    await update_coins(user_id, total_reward)
    completed_tasks = await update_task_progress(user_id, "daily")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET daily_claimed = ? WHERE user_id = ?", (today.isoformat(), user_id))
    conn.commit()
    conn.close()
    text = f"Ежедневный бонус!\n"
    text += f"Награда: +{total_reward} монет\n"
    text += f"Серия дней: {new_streak}\n"
    text += f"Лучшая серия: {best_streak}\n"
    if new_streak in STREAK_REWARDS:
        text += f"{reward_desc}!\n"
        text += f"Ты получил бонус за серию!\n"
    else:
        text += f"{reward_desc}\n"
    next_streaks = sorted([s for s in STREAK_REWARDS.keys() if s > new_streak])
    if next_streaks:
        next_streak = next_streaks[0]
        days_left = next_streak - new_streak
        text += f"Следующий бонус через {days_left} дн. ({next_streak} дней = {STREAK_REWARDS[next_streak]['coins']} монет)"
    await safe_send(message, text, reply_markup=back_to_menu_keyboard())
    if new_streak >= 30:
        await send_sticker(message, "streak_30")
    elif new_streak >= 7:
        await send_sticker(message, "streak_7")
    if completed_tasks:
        await asyncio.sleep(1)
        for task in completed_tasks:
            await safe_send(message,
                            f"Задание выполнено!\n"
                            f"{task['name']}\n"
                            f"Награда: +{task['reward']} монет\n"
                            f"Забери награду в разделе Задания")
    new_achievements = await check_and_award_achievements(user_id)
    if new_achievements:
        await asyncio.sleep(1)
        for ach in new_achievements:
            await send_sticker(message, "achievement")
            await safe_send(message,
                            f"Новое достижение!\n{ach['name']}\n{ach['description']}\n+{ach['reward']} монет")


@dp.message(Command("streak"))
@dp.callback_query(lambda c: c.data == "streak_info")
async def show_streak(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    streak_info = await get_streak_info(user_id)
    text = f"Твоя серия дней\n"
    text += f"Текущая серия: {streak_info['current']} дн.\n"
    text += f"Лучшая серия: {streak_info['best']} дн.\n"
    text += f"Статус: {streak_info['status']}\n"
    text += "Бонусы за серию:\n"
    for days, reward in sorted(STREAK_REWARDS.items()):
        if days <= streak_info["current"]:
            text += f"✅ {days} дн. - {reward['coins']} монет ({reward['description']})\n"
        else:
            text += f"🔒 {days} дн. - {reward['coins']} монет ({reward['description']})\n"
    await safe_send(message, text, reply_markup=streak_info_keyboard())


@dp.message(Command("leaderboard"))
@dp.message(Command("rating"))
@dp.callback_query(lambda c: c.data == "leaderboard")
async def show_leaderboard(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        await callback.answer()
    else:
        message = callback
    await safe_send(message, "Рейтинг\nВыбери категорию:",
                    reply_markup=leaderboard_keyboard())


@dp.callback_query(lambda c: c.data == "lb_cards")
async def leaderboard_cards(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    top = await get_leaderboard_by_cards(10)
    user_rank = await get_user_rank(callback.from_user.id)
    text = "Топ по карточкам\n"
    for i, (user_id, username, unique_cards) in enumerate(top, 1):
        medals = ["🥇", "🥈", "🥉"]
        medal = medals[i - 1] if i <= 3 else f"{i}."
        username = username or "Без имени"
        marker = " - Ты" if user_id == callback.from_user.id else ""
        text += f"{medal} @{username} - {unique_cards} карточек{marker}\n"
    if user_rank and user_rank > 10:
        text += f"\n... твоё место: номер {user_rank}"
    elif not user_rank:
        text += "\nТы ещё не в рейтинге"
    await callback.message.edit_text(text, reply_markup=leaderboard_keyboard())


@dp.callback_query(lambda c: c.data == "lb_coins")
async def leaderboard_coins(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    top = await get_leaderboard_by_coins(10)
    text = "Топ по монетам\n"
    for i, (user_id, username, coins) in enumerate(top, 1):
        medals = ["🥇", "🥈", "🥉"]
        medal = medals[i - 1] if i <= 3 else f"{i}."
        username = username or "Без имени"
        marker = " - Ты" if user_id == callback.from_user.id else ""
        text += f"{medal} @{username} - {coins:,} монет{marker}\n"
    await callback.message.edit_text(text, reply_markup=leaderboard_keyboard())


@dp.callback_query(lambda c: c.data == "lb_streak")
async def leaderboard_streak(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    top = await get_leaderboard_by_streak(10)
    text = "Топ по серии дней\n"
    if not top:
        text += "Пока никто не получал ежедневный бонус"
    else:
        for i, (user_id, username, current_streak, best_streak) in enumerate(top, 1):
            medals = ["🥇", "🥈", "🥉"]
            medal = medals[i - 1] if i <= 3 else f"{i}."
            username = username or "Без имени"
            marker = " - Ты" if user_id == callback.from_user.id else ""
            text += f"{medal} @{username} - {current_streak} дн. (лучшая: {best_streak}){marker}\n"
    await callback.message.edit_text(text, reply_markup=leaderboard_keyboard())


@dp.message(Command("tasks"))
@dp.callback_query(lambda c: c.data == "daily_tasks")
async def show_daily_tasks(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    tasks = await get_daily_tasks(user_id)
    completed_today = sum(1 for t in tasks if t["completed"])
    total = len(tasks)
    text = f"Ежедневные задания\n"
    text += f"Выполнено сегодня: {completed_today} из {total}\n"
    text += "Нажми на задание, чтобы забрать награду:\n"
    await safe_send(message, text, reply_markup=daily_tasks_keyboard(tasks))


@dp.callback_query(lambda c: c.data == "task_info")
async def task_info(callback: types.CallbackQuery):
    await callback.answer("Задание ещё не выполнено. Продолжай играть!", show_alert=True)


@dp.callback_query(lambda c: c.data.startswith("task_claim_"))
async def claim_task(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    task_key = callback.data.replace("task_claim_", "")
    success, reward, msg = await claim_task_reward(callback.from_user.id, task_key)
    if success:
        if await is_premium(callback.from_user.id):
            reward *= 2
        await update_coins(callback.from_user.id, reward)
        await callback.message.answer(
            f"Награда получена!\n"
            f"+{reward} монет\n"
            f"Проверь свой кошелёк: /wallet",
            reply_markup=back_to_menu_keyboard()
        )
        new_achievements = await check_and_award_achievements(callback.from_user.id)
        if new_achievements:
            await asyncio.sleep(1)
            for ach in new_achievements:
                await send_sticker(callback.message, "achievement")
                await safe_send(callback.message,
                                f"Новое достижение!\n{ach['name']}\n{ach['description']}\n+{ach['reward']} монет")
    else:
        await callback.message.answer(msg, reply_markup=back_to_menu_keyboard())


# ============================================
# МАГАЗИН (исправлен shop_confirm)
# ============================================
@dp.message(Command("shop"))
@dp.callback_query(lambda c: c.data == "shop_main")
async def show_shop(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    coins = user[2]
    text = (
        f"Магазин\n"
        f"Твой баланс: {coins} монет\n"
        f"Выбери категорию:"
    )
    await safe_send(message, text, reply_markup=shop_main_keyboard())


@dp.callback_query(lambda c: c.data == "shop_items")
async def shop_items(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    text = (
        "Предметы\n"
        "Пропуск - 250 монет\n"
        "   Пропускает кулдаун один раз\n"
        "Таймер - 2000 монет\n"
        "   Снижает кулдаун на 30 мин. навсегда\n"
        "Золотой таймер - 7500 монет\n"
        "   Снижает кулдаун на 2 часа навсегда\n"
        "Пакет - 12000 монет\n"
        "   Позволяет получать 2 карточки за раз\n"
        "Нажми на предмет для покупки:"
    )
    await callback.message.edit_text(text, reply_markup=shop_items_keyboard())


@dp.callback_query(lambda c: c.data == "shop_packs")
async def shop_packs(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    text = (
        "Наборы карточек\n"
        "Обычный набор - 200 монет\n"
        "   2-3 карточки (макс. Rare)\n"
        "Профессиональный - 1000 монет\n"
        "   4-6 карточек (макс. Legendary)\n"
        "Премиум - 4500 монет\n"
        "   8-12 карточек (шанс Secret 1.4%)\n"
        "Нажми на набор для покупки:"
    )
    await callback.message.edit_text(text, reply_markup=shop_packs_keyboard())


@dp.callback_query(lambda c: c.data == "shop_cases")
async def shop_cases(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    text = (
        "Кейсы\n"
        "Деревянный - 120 монет\n"
        "   1-2 карточки + шанс на Пропуск\n"
        "Железный - 400 монет\n"
        "   2-3 карточки + шанс на Таймер\n"
        "Золотой - 1200 монет\n"
        "   3-5 карточек + шанс на Пропуск/Таймер\n"
        "Платиновый - 3500 монет\n"
        "   5-8 карточек + шанс на Золотой таймер/Пакет\n"
        "Кристальный - 8000 монет\n"
        "   8-12 карточек + повышенный шанс Secret\n"
        "Нажми на кейс для покупки:"
    )
    await callback.message.edit_text(text, reply_markup=shop_cases_keyboard())


@dp.callback_query(lambda c: c.data.startswith("shop_buy_"))
async def shop_buy(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    item_key = callback.data.replace("shop_buy_", "")
    item = SHOP_ITEMS.get(item_key)
    case = CASES.get(item_key)
    if not item and not case:
        await callback.message.answer("Предмет не найден", reply_markup=back_to_menu_keyboard())
        return
    if item:
        text = (
            f"{item['name']}\n"
            f"{item['description']}\n"
            f"Цена: {item['price']} монет"
        )
        keyboard = buy_item_keyboard(item_key, item['price'])
    else:
        text = (
            f"{case['name']}\n"
            f"{case['description']}\n"
            f"Цена: {case['price']} монет"
        )
        keyboard = buy_case_keyboard(item_key, case['price'])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("shop_confirm_"))
async def shop_confirm(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    item_key = callback.data.replace("shop_confirm_", "")
    user_id = callback.from_user.id
    item = SHOP_ITEMS.get(item_key)
    case = CASES.get(item_key)
    if not item and not case:
        await callback.message.answer("Предмет не найден", reply_markup=back_to_menu_keyboard())
        return
    if item:
        price = item['price']
    else:
        price = case['price']
    coins = await get_user_coins(user_id)
    if coins < price:
        await callback.message.answer(
            f"Недостаточно монет!\n"
            f"Нужно: {price} монет\n"
            f"У тебя: {coins} монет\n"
            f"Заработай больше монет через /daily и задания!",
            reply_markup=back_to_menu_keyboard()
        )
        return
    await update_coins(user_id, -price)
    await record_purchase(user_id, item_key, price)
    if item:
        if item["type"] == "permanent":
            if item["effect"] == "cooldown_minus_30min":
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET cooldown_reduction_minutes = cooldown_reduction_minutes + 30 WHERE user_id = ?",
                    (user_id,))
                conn.commit()
                conn.close()
                text = f"Куплено: {item['name']}\nТвой кулдаун снижен на 30 минут навсегда!"
            elif item["effect"] == "cooldown_minus_2h":
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET cooldown_reduction_minutes = cooldown_reduction_minutes + 120 WHERE user_id = ?",
                    (user_id,))
                conn.commit()
                conn.close()
                text = f"Куплено: {item['name']}\nТвой кулдаун снижен на 2 часа навсегда!"
            elif item["effect"] == "double_claim":
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET extra_claims = extra_claims + 1 WHERE user_id = ?", (user_id,))
                conn.commit()
                conn.close()
                text = f"Куплено: {item['name']}\nТеперь ты можешь получать 2 карточки за раз!"
            else:
                await add_item(user_id, item_key, 1)
                text = f"Куплено: {item['name']}\nПредмет добавлен в инвентарь. Используй /inventory"
        else:
            await add_item(user_id, item_key, 1)
            text = f"Куплено: {item['name']}\nПредмет добавлен в инвентарь. Используй /inventory"
    else:
        result, error = await open_case(user_id, item_key)
        if error:
            # Возвращаем монеты при ошибке
            await update_coins(user_id, price)
            await callback.message.answer(f"Ошибка: {error}", reply_markup=back_to_menu_keyboard())
            return
        cards = result.get("cards", [])
        items = result.get("items", [])
        if not cards and not items:
            await callback.message.answer(
                f"{case['name']} открыт, но ничего не выпало. Попробуй ещё!",
                reply_markup=back_to_menu_keyboard()
            )
            return
        text = f"{case['name']} открыт!\n"
        text += f"Получено карточек: {len(cards)}\n"
        for card in cards:
            rarity_color = get_rarity_color(card[4])
            text += f"{rarity_color} {card[1]} ({card[4].capitalize()})\n"
            bonus = RARITIES[card[4]]["multiplier"]
            if await is_premium(user_id):
                bonus *= 2
            if bonus > 1:
                await update_coins(user_id, bonus)
        if items:
            text += "\nПолучены предметы:\n"
            for item_key in items:
                item_info = SHOP_ITEMS.get(item_key)
                if item_info:
                    text += f"- {item_info['name']}\n"
        text += "\nКарточки добавлены в коллекцию!"
        for i, card in enumerate(cards):
            card_path = os.path.join(CARDS_FOLDER, card[3])
            if os.path.exists(card_path):
                try:
                    photo = FSInputFile(card_path)
                    rarity_color = get_rarity_color(card[4])
                    caption = f"Карточка {i + 1} из {len(cards)}\n{rarity_color} {card[1]}\n{card[2]}\n{card[4].capitalize()}"
                    await callback.message.answer_photo(photo=photo, caption=caption)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Ошибка отправки фото: {e}")
    completed_tasks = await update_task_progress(user_id, "shop")
    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    if completed_tasks:
        await asyncio.sleep(1)
        for task in completed_tasks:
            await safe_send(callback.message,
                            f"Задание выполнено!\n"
                            f"{task['name']}\n"
                            f"Награда: +{task['reward']} монет")
    new_achievements = await check_and_award_achievements(user_id)
    if new_achievements:
        await asyncio.sleep(1)
        for ach in new_achievements:
            await send_sticker(callback.message, "achievement")
            await safe_send(callback.message,
                            f"Новое достижение!\n{ach['name']}\n{ach['description']}\n+{ach['reward']} монет")


@dp.message(Command("inventory"))
@dp.callback_query(lambda c: c.data == "inventory")
async def show_inventory(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    items = await get_user_items(user_id)
    if not items:
        text = (
            "Твой инвентарь\n"
            "Инвентарь пуст\n"
            "Купи предметы в магазине: /shop"
        )
        await safe_send(message, text, reply_markup=shop_main_keyboard())
        return
    text = "Твой инвентарь\n"
    for item_key, quantity in items.items():
        item = SHOP_ITEMS.get(item_key)
        if item:
            text += f"{item['name']} x{quantity}\n"
            text += f"  {item['description']}\n"
    text += "\nНажми на предмет, чтобы использовать:"
    await safe_send(message, text, reply_markup=inventory_keyboard(items))


@dp.callback_query(lambda c: c.data.startswith("inv_use_"))
async def inv_use(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    item_key = callback.data.replace("inv_use_", "")
    user_id = callback.from_user.id
    quantity = await get_item_quantity(user_id, item_key)
    if quantity <= 0:
        await callback.message.answer("У тебя нет этого предмета!", reply_markup=back_to_menu_keyboard())
        return
    if item_key == "skip":
        success, msg = await use_skip(user_id)
        if success:
            await callback.message.answer(
                f"Пропуск использован!\n"
                f"Теперь ты можешь получить карточку.\n"
                f"Используй /claim",
                reply_markup=back_to_menu_keyboard()
            )
        else:
            await callback.message.answer(msg, reply_markup=back_to_menu_keyboard())
    elif item_key == "timer":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET cooldown_reduction_minutes = cooldown_reduction_minutes + 30 WHERE user_id = ?",
            (user_id,))
        conn.commit()
        conn.close()
        await remove_item(user_id, item_key, 1)
        await callback.message.answer(
            f"Таймер применён!\n"
            f"Твой кулдаун снижен на 30 минут навсегда!",
            reply_markup=back_to_menu_keyboard()
        )
    elif item_key == "gold_timer":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET cooldown_reduction_minutes = cooldown_reduction_minutes + 120 WHERE user_id = ?",
            (user_id,))
        conn.commit()
        conn.close()
        await remove_item(user_id, item_key, 1)
        await callback.message.answer(
            f"Золотой таймер применён!\n"
            f"Твой кулдаун снижен на 2 часа навсегда!",
            reply_markup=back_to_menu_keyboard()
        )
    elif item_key == "pack":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET extra_claims = extra_claims + 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await remove_item(user_id, item_key, 1)
        await callback.message.answer(
            f"Пакет активирован!\n"
            f"При следующем /claim ты получишь 2 карточки вместо одной!",
            reply_markup=back_to_menu_keyboard()
        )
    elif item_key in ["pack_normal", "pack_pro", "pack_premium"]:
        item = SHOP_ITEMS.get(item_key)
        if not item:
            await callback.message.answer("Предмет не найден!", reply_markup=back_to_menu_keyboard())
            return
        pack_config = item.get("pack_config", {})
        cards_received = await open_pack(user_id, pack_config)
        await remove_item(user_id, item_key, 1)
        if not cards_received:
            await callback.message.answer("К сожалению, сейчас нет доступных карточек!",
                                          reply_markup=back_to_menu_keyboard())
            return
        pack_text = f"{item['name']} открыт!\n"
        pack_text += f"Получено карточек: {len(cards_received)}\n"
        for card in cards_received:
            rarity_color = get_rarity_color(card[4])
            pack_text += f"{rarity_color} {card[1]} - {card[2]} [{card[4].capitalize()}]\n"
            bonus = RARITIES[card[4]]["multiplier"]
            if await is_premium(user_id):
                bonus *= 2
            if bonus > 1:
                await update_coins(user_id, bonus)
        pack_text += f"\nБонусы за редкость начислены!"
        await callback.message.answer(pack_text, reply_markup=back_to_menu_keyboard())
        for i, card in enumerate(cards_received):
            card_path = os.path.join(CARDS_FOLDER, card[3])
            if os.path.exists(card_path):
                try:
                    photo = FSInputFile(card_path)
                    rarity_color = get_rarity_color(card[4])
                    caption = f"Карточка {i + 1} из {len(cards_received)}\n{rarity_color} {card[1]}\n{card[2]}\n{card[4].capitalize()}"
                    await callback.message.answer_photo(photo=photo, caption=caption)
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Ошибка отправки фото: {e}")
    else:
        await callback.message.answer(
            "Этот предмет не имеет ручного применения.",
            reply_markup=back_to_menu_keyboard()
        )


# ============================================
# АУКЦИОНЫ И РЫНОК (без изменений)
# ============================================
@dp.message(Command("auction"))
@dp.callback_query(lambda c: c.data == "auction_main")
async def show_auctions(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        await callback.answer()
    else:
        message = callback
    try:
        auctions = await get_active_auctions(20)
    except Exception as e:
        logger.error(f"Ошибка получения аукционов: {e}")
        await safe_send(message,
                        "Ошибка загрузки аукционов. Попробуй позже.",
                        reply_markup=main_menu_keyboard())
        return
    if not auctions:
        await safe_send(message,
                        "Активные аукционы\n"
                        "Сейчас нет активных аукционов.\n"
                        "Будь первым, кто выставит карточку!\n"
                        "Используй: /sell номер_карточки стартовая_цена\n"
                        "Минимальная стартовая цена: 100 монет",
                        reply_markup=main_menu_keyboard())
        return
    text = "Активные аукционы\n"
    text += f"Минимальный шаг ставки: {AUCTION_MIN_BID_INCREMENT} монет\n"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    for auction in auctions:
        try:
            aid = auction[0]
            seller_id = auction[2]
            start_price = auction[3]
            current_bid = auction[4]
            end_time = auction[6]
            username = auction[8]
            name = auction[9]
            rarity = auction[10]
            artist = auction[11]
            color = get_rarity_color(rarity)
            username = username or "Unknown"
            time_left = datetime.fromisoformat(end_time) - datetime.now()
            if time_left.total_seconds() > 0:
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                time_str = f"{hours} ч. {minutes} мин."
            else:
                time_str = "Завершается..."
            current = current_bid if current_bid > 0 else start_price
            text += f"{color} Аукцион {aid} - {name}\n"
            text += f"Продавец: @{username}\n"
            text += f"Текущая ставка: {current} монет\n"
            text += f"Осталось: {time_str}\n"
            text += f"{artist} ({rarity.capitalize()})\n"
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text=f"Ставка на аукцион {aid}",
                    callback_data=f"auction_bid_{aid}"
                )
            ])
        except Exception as e:
            logger.error(f"Ошибка обработки аукциона: {e}")
            continue
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="Назад", callback_data="main_menu")
    ])
    await safe_send(message, text, reply_markup=keyboard)


@dp.message(Command("myauctions"))
async def my_auctions(message: types.Message):
    user_id = message.from_user.id
    auctions = await get_user_auctions(user_id)
    if not auctions:
        await message.answer(
            "Мои аукционы\n"
            "У тебя нет активных аукционов.\n"
            "Выставить карточку: /sell номер_карточки цена"
        )
        return
    text = "Мои аукционы\n"
    for auction in auctions:
        aid = auction[0]
        start_price = auction[2]
        current_bid = auction[3]
        end_time = auction[4]
        status = auction[5]
        name = auction[6]
        rarity = auction[7]
        color = get_rarity_color(rarity)
        time_left = datetime.fromisoformat(end_time) - datetime.now()
        if time_left.total_seconds() > 0:
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            time_str = f"{hours} ч. {minutes} мин."
        else:
            time_str = "Завершено"
        status_emoji = "🟢" if status == "active" else "🔴"
        text += f"{status_emoji} {color} Аукцион {aid} - {name} ({rarity.capitalize()})\n"
        text += f"Текущая ставка: {current_bid if current_bid > 0 else start_price} монет\n"
        text += f"Осталось: {time_str}\n"
    await message.answer(text)


@dp.message(Command("sell"))
async def sell_card(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "Выставить на аукцион\n"
            "Использование: /sell номер_карточки стартовая_цена\n"
            "Пример: /sell 42 500\n"
            "Чтобы увидеть номера своих карточек: /mycards\n"
            f"Аукцион длится {AUCTION_DURATION_HOURS} часов\n"
            "Минимальная стартовая цена: 100 монет"
        )
        return
    try:
        card_id = int(args[1])
        start_price = int(args[2])
    except ValueError:
        await message.answer("Номер и цена должны быть числами!")
        return
    if start_price < 100:
        await message.answer("Минимальная стартовая цена: 100 монет")
        return
    user_id = message.from_user.id
    count = await get_user_card_count(user_id, card_id)
    if count <= 0:
        await message.answer("У тебя нет такой карточки!")
        return
    auction_id, error = await create_auction(user_id, card_id, start_price, AUCTION_DURATION_HOURS)
    if error:
        await message.answer(error)
        return
    card = await get_card_by_id(card_id)
    await message.answer(
        f"Карточка выставлена на аукцион!\n"
        f"{get_rarity_color(card[4])} {card[1]} ({card[4].capitalize()})\n"
        f"Стартовая цена: {start_price} монет\n"
        f"Длительность: {AUCTION_DURATION_HOURS} часов\n"
        f"Комиссия: {AUCTION_FEE_PERCENT}%\n"
        f"Номер аукциона: {auction_id}\n"
        f"Посмотреть аукционы: /auction"
    )


@dp.message(Command("bid"))
async def bid_command(message: types.Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "Сделать ставку\n"
            "Использование: /bid номер_аукциона сумма\n"
            "Пример: /bid 42 600\n"
            "Посмотреть аукционы: /auction"
        )
        return
    try:
        auction_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("Номер и сумма должны быть числами!")
        return
    buyer_id = message.from_user.id
    success, msg = await place_bid(auction_id, buyer_id, amount)
    await message.answer(msg)


@dp.callback_query(lambda c: c.data.startswith("auction_bid_"))
async def auction_bid(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        auction_id = int(callback.data.replace("auction_bid_", ""))
    except ValueError:
        await callback.message.answer("Ошибка!")
        return
    auction = await get_auction(auction_id)
    if not auction:
        await callback.message.answer("Аукцион не найден!")
        return
    seller_id = auction[2]
    start_price = auction[3]
    current_bid = auction[4]
    if seller_id == callback.from_user.id:
        await callback.message.answer("Нельзя ставить ставку на свой лот!")
        return
    min_bid = max(start_price, current_bid) + AUCTION_MIN_BID_INCREMENT
    await state.update_data(bid_auction_id=auction_id, bid_min_amount=min_bid)
    await callback.message.edit_text(
        f"Сделать ставку на аукцион {auction_id}\n"
        f"Текущая ставка: {current_bid if current_bid > 0 else start_price} монет\n"
        f"Минимальная ставка: {min_bid} монет\n"
        f"Введи сумму ставки:",
        reply_markup=back_to_menu_keyboard()
    )
    await state.set_state(UserStates.waiting_for_bid_amount)


@dp.message(UserStates.waiting_for_bid_amount)
async def process_bid_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer("Сумма должна быть числом! Попробуй ещё раз:")
        return
    data = await state.get_data()
    auction_id = data.get('bid_auction_id')
    min_amount = data.get('bid_min_amount')
    if amount < min_amount:
        await message.answer(f"Сумма должна быть не меньше {min_amount} монет!")
        return
    buyer_id = message.from_user.id
    success, msg = await place_bid(auction_id, buyer_id, amount)
    await message.answer(msg, reply_markup=back_to_menu_keyboard())
    await state.clear()


@dp.message(Command("market"))
@dp.callback_query(lambda c: c.data == "market_main")
async def market_main(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        await callback.answer()
    else:
        message = callback
    await safe_send(message,
                    "Рынок\n"
                    "Покупай и продавай карточки по фиксированной цене!\n"
                    "Комиссия при продаже: 10%\n"
                    "Цена: от 1 до 1 000 000 монет",
                    reply_markup=market_main_keyboard())


@dp.callback_query(lambda c: c.data == "market_list")
async def market_list(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        listings = await get_active_listings(20)
    except Exception as e:
        logger.error(f"Ошибка получения объявлений: {e}")
        await callback.message.edit_text("Ошибка загрузки рынка", reply_markup=market_main_keyboard())
        return
    if not listings:
        await callback.message.edit_text(
            "Рынок\n"
            "Сейчас нет активных объявлений.\n"
            "Будь первым, кто выставит карточку!\n"
            "Используй: /sell номер_карточки цена",
            reply_markup=market_main_keyboard()
        )
        return
    text = "Активные объявления\n"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    for listing in listings:
        try:
            lid = listing[0]
            seller_id = listing[2]
            price = listing[3]
            username = listing[6]
            name = listing[7]
            rarity = listing[8]
            artist = listing[9]
            color = get_rarity_color(rarity)
            username = username or "Unknown"
            text += f"{color} Артикул {lid} - {name}\n"
            text += f"Продавец: @{username}\n"
            text += f"Цена: {price} монет\n"
            text += f"{artist} ({rarity.capitalize()})\n"
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text=f"Купить за {price}",
                    callback_data=f"market_buy_{lid}"
                )
            ])
        except Exception as e:
            logger.error(f"Ошибка обработки объявления: {e}")
            continue
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="Назад", callback_data="market_main")
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "market_mine")
async def market_mine(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    listings = await get_user_listings(callback.from_user.id)
    if not listings:
        await callback.message.edit_text(
            "Мои объявления\n"
            "У тебя нет активных объявлений.\n"
            "Выставить карточку: /sell номер_карточки цена",
            reply_markup=market_main_keyboard()
        )
        return
    text = "Мои объявления\n"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    for listing in listings:
        lid = listing[0]
        price = listing[2]
        status = listing[4]
        name = listing[5]
        rarity = listing[6]
        color = get_rarity_color(rarity)
        status_emoji = "🟢" if status == "active" else "🔴"
        text += f"{status_emoji} {color} Артикул {lid} - {name} ({rarity.capitalize()})\n"
        text += f"Цена: {price} монет\n"
        if status == "active":
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text=f"Просмотреть {lid}",
                    callback_data=f"market_view_{lid}"
                )
            ])
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="Назад", callback_data="market_main")
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "market_sell")
async def market_sell(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    user_id = callback.from_user.id
    can_create, current_count, limit = await can_create_listing(user_id)
    if not can_create:
        await callback.message.edit_text(
            f"⚠️ Лимит рынка!\n"
            f"Ты уже выставил {current_count} из {limit} карточек на продажу.\n"
            f"Сними карточки с продажи или дождись покупки, чтобы выставить новые.\n"
            f"💎 Premium пользователи имеют безлимитный лимит!",
            reply_markup=market_main_keyboard()
        )
        return
    collection = await get_user_collection(user_id)
    if not collection:
        await callback.message.edit_text(
            "Выставить на продажу\n"
            "У тебя нет карточек для продажи!\n"
            "Получи карточку: /claim",
            reply_markup=market_main_keyboard()
        )
        return
    text = "Выбери карточку для продажи:\n"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    for card in collection[:20]:
        card_id = card[0]
        count = card[1]
        name = card[2]
        rarity = card[4]
        color = get_rarity_color(rarity)
        button_text = f"{color} {name} (Номер: {card_id}) x{count}"
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(text=button_text, callback_data=f"market_set_price_{card_id}")
        ])
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="Назад", callback_data="market_main")
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("market_set_price_"))
async def market_set_price(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        card_id = int(callback.data.replace("market_set_price_", ""))
    except ValueError:
        await callback.message.answer("Ошибка!")
        return
    count = await get_user_card_count(callback.from_user.id, card_id)
    if count <= 0:
        await callback.message.answer("У тебя нет такой карточки!")
        return
    card = await get_card_by_id(card_id)
    if not card:
        await callback.message.answer("Карточка не найдена!")
        return
    await state.update_data(market_card_id=card_id)
    await callback.message.edit_text(
        f"Продажа карточки\n"
        f"{get_rarity_color(card[4])} {card[1]} ({card[4].capitalize()})\n"
        f"{card[2]}\n"
        f"Введи цену (от 1 до 1 000 000 монет):\n"
        f"При продаже ты получишь: цена минус 10% комиссии",
        reply_markup=market_main_keyboard()
    )
    await state.set_state(UserStates.waiting_for_market_price)


@dp.message(UserStates.waiting_for_market_price)
async def process_market_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
    except ValueError:
        await message.answer("Цена должна быть числом! Попробуй ещё раз:")
        return
    if price < 1:
        await message.answer("Минимальная цена: 1 монета")
        return
    if price > 1000000:
        await message.answer("Максимальная цена: 1 000 000 монет")
        return
    data = await state.get_data()
    card_id = data.get('market_card_id')
    if not card_id:
        await message.answer("Ошибка! Начни заново: /market")
        await state.clear()
        return
    count = await get_user_card_count(message.from_user.id, card_id)
    if count <= 0:
        await message.answer("У тебя больше нет этой карточки!")
        await state.clear()
        return
    listing_id, error = await create_listing(message.from_user.id, card_id, price)
    if error:
        await message.answer(error)
        await state.clear()
        return
    card = await get_card_by_id(card_id)
    seller_receives = price - int(price * 0.10)
    await message.answer(
        f"Карточка выставлена на рынок!\n"
        f"{get_rarity_color(card[4])} {card[1]} ({card[4].capitalize()})\n"
        f"Цена: {price} монет\n"
        f"Артикул: {listing_id}\n"
        f"При продаже ты получишь: {seller_receives} монет (комиссия 10%)\n"
        f"Посмотреть рынок: /market",
        reply_markup=market_main_keyboard()
    )
    await state.clear()


@dp.callback_query(lambda c: c.data.startswith("market_buy_"))
async def market_buy(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        listing_id = int(callback.data.replace("market_buy_", ""))
    except ValueError:
        await callback.message.answer("Ошибка!")
        return
    listing = await get_listing(listing_id)
    if not listing:
        await callback.message.answer("Объявление не найдено!", reply_markup=market_main_keyboard())
        return
    lid = listing[0]
    card_id = listing[1]
    seller_id = listing[2]
    price = listing[3]
    username = listing[6]
    name = listing[7]
    rarity = listing[8]
    color = get_rarity_color(rarity)
    if seller_id == callback.from_user.id:
        await callback.message.answer("Нельзя купить свою карточку!", reply_markup=market_main_keyboard())
        return
    buyer_coins = await get_user_coins(callback.from_user.id)
    if buyer_coins < price:
        await callback.message.answer(
            f"Недостаточно монет!\n"
            f"Нужно: {price} монет\n"
            f"У тебя: {buyer_coins} монет",
            reply_markup=market_main_keyboard()
        )
        return
    success, msg = await buy_listing(listing_id, callback.from_user.id)
    if success:
        await callback.message.answer(
            f"Покупка успешна!\n"
            f"{color} {name} ({rarity.capitalize()})\n"
            f"Списано: {price} монет\n"
            f"Проверь коллекцию: /mycards",
            reply_markup=market_main_keyboard()
        )
        try:
            seller_receives = price - int(price * 0.10)
            await bot.send_message(
                seller_id,
                f"Твоя карточка продана!\n"
                f"{color} {name}\n"
                f"Ты получил: {seller_receives} монет\n"
                f"(комиссия 10%: {int(price * 0.10)} монет)"
            )
        except:
            pass
    else:
        await callback.message.answer(msg, reply_markup=market_main_keyboard())


@dp.callback_query(lambda c: c.data.startswith("market_cancel_"))
async def market_cancel(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        listing_id = int(callback.data.replace("market_cancel_", ""))
    except ValueError:
        await callback.message.answer("Ошибка!")
        return
    success, msg = await cancel_listing(listing_id, callback.from_user.id)
    await callback.message.answer(
        f"{'✅' if success else '❌'} {msg}",
        reply_markup=market_main_keyboard()
    )


@dp.callback_query(lambda c: c.data.startswith("market_view_"))
async def market_view(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        listing_id = int(callback.data.replace("market_view_", ""))
    except ValueError:
        await callback.message.answer("Ошибка!")
        return
    listing = await get_listing(listing_id)
    if not listing:
        await callback.message.edit_text("Объявление не найдено.", reply_markup=market_main_keyboard())
        return
    lid = listing[0]
    card_id = listing[1]
    seller_id = listing[2]
    price = listing[3]
    status = listing[5]
    username = listing[6]
    name = listing[7]
    rarity = listing[8]
    artist = listing[9]
    color = get_rarity_color(rarity)
    is_owner = (seller_id == callback.from_user.id)
    text = f"Артикул {lid}\n"
    text += f"{color} {name}\n"
    text += f"Художник: {artist}\n"
    text += f"Редкость: {rarity.capitalize()}\n"
    text += f"Продавец: @{username or 'Unknown'}\n"
    text += f"Цена: {price} монет\n"
    text += f"Статус: {'🟢 Активно' if status == 'active' else '🔴 Продано'}\n"
    if status == 'active':
        fee = int(price * 0.10)
        text += f"При покупке ты заплатишь: {price} монет\n"
        if is_owner:
            text += f"При продаже ты получишь: {price - fee} монет"
    keyboard = market_listing_keyboard(lid, is_owner)
    await callback.message.edit_text(text, reply_markup=keyboard)


# ============================================
# ОБМЕНЫ (без изменений)
# ============================================
@dp.message(Command("trades"))
@dp.callback_query(lambda c: c.data == "trades")
async def show_trades(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        await callback.answer()
    else:
        message = callback
    await safe_send(message,
                    "Обмены\n"
                    "Выбери действие:",
                    reply_markup=trades_menu_keyboard())


@dp.callback_query(lambda c: c.data == "trades_incoming")
async def trades_incoming(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    offers = await get_trade_offers_for_user(callback.from_user.id)
    if not offers:
        await callback.message.edit_text(
            "Входящие предложения\n"
            "У тебя нет входящих предложений обмена.\n"
            "Попроси другого игрока создать обмен!",
            reply_markup=trades_menu_keyboard()
        )
        return
    text = "Входящие предложения\n"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    for offer in offers:
        offer_id = offer[0]
        from_user = offer[1]
        from_card = offer[3]
        to_card = offer[4]
        from_card_info = await get_card_by_id(from_card)
        to_card_info = await get_card_by_id(to_card)
        from_user_data = await get_user(from_user)
        from_username = from_user_data[1] if from_user_data else 'Unknown'
        if from_card_info and to_card_info:
            text += f"Предложение {offer_id}\n"
            text += f"От: @{from_username}\n"
            text += f"Даёт: {from_card_info[1]} ({get_rarity_color(from_card_info[4])})\n"
            text += f"Просит: {to_card_info[1]} ({get_rarity_color(to_card_info[4])})\n"
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text=f"Просмотреть {offer_id}",
                    callback_data=f"trade_view_{offer_id}"
                )
            ])
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="Назад", callback_data="trades")
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "trades_outgoing")
async def trades_outgoing(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    offers = await get_trade_offers_from_user(callback.from_user.id)
    if not offers:
        await callback.message.edit_text(
            "Мои предложения\n"
            "Ты ещё не создавал предложений обмена.",
            reply_markup=trades_menu_keyboard()
        )
        return
    text = "Мои предложения\n"
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
    for offer in offers:
        offer_id = offer[0]
        to_user = offer[2]
        to_card = offer[4]
        to_card_info = await get_card_by_id(to_card)
        to_user_data = await get_user(to_user)
        to_username = to_user_data[1] if to_user_data else 'Unknown'
        if to_card_info:
            text += f"Предложение {offer_id}\n"
            text += f"Для: @{to_username}\n"
            text += f"Ты просишь: {to_card_info[1]}\n"
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text=f"Просмотреть {offer_id}",
                    callback_data=f"trade_view_{offer_id}"
                )
            ])
    keyboard.inline_keyboard.append([
        types.InlineKeyboardButton(text="Назад", callback_data="trades")
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "trade_create")
async def trade_create(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    await callback.message.edit_text(
        "Создать обмен\n"
        "Как найти игрока для обмена?",
        reply_markup=trade_create_keyboard()
    )


@dp.callback_query(lambda c: c.data == "trade_by_username")
async def trade_by_username(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    await callback.message.edit_text("Введи username игрока (без @):\nНапример: username")
    await state.set_state(UserStates.waiting_for_trade_username)


@dp.message(UserStates.waiting_for_trade_username)
async def process_trade_username(message: types.Message, state: FSMContext):
    username = message.text.strip().lstrip('@')
    user_id = await get_user_by_username(username)
    if not user_id:
        await message.answer(
            f"Пользователь @{username} не найден в базе бота.\n"
            f"Возможные причины:\n"
            f"- Пользователь ещё не запускал бота (не нажал /start)\n"
            f"- Username написан с ошибкой\n"
            f"Попроси друга написать боту /start, а затем попробуй снова!\n"
            f"Или используй /trades для возврата:"
        )
        return
    if user_id == message.from_user.id:
        await message.answer("Нельзя обмениваться с самим собой!")
        return
    await state.update_data(trade_to_user=user_id, trade_to_username=username)
    await message.answer(
        f"Игрок найден: @{username}\n"
        f"Теперь введи номер карточки, которую ты хочешь ОТДАТЬ:\n"
        f"Посмотри свою коллекцию: /mycards",
        reply_markup=back_to_menu_keyboard()
    )
    await state.set_state(UserStates.waiting_for_trade_from_card)


@dp.callback_query(lambda c: c.data == "trade_by_id")
async def trade_by_id(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    await callback.message.edit_text("Введи ID игрока:\nНапример: 123456789")
    await state.set_state(UserStates.waiting_for_trade_user_id)


@dp.message(UserStates.waiting_for_trade_user_id)
async def process_trade_user_id(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except ValueError:
        await message.answer("ID должен быть числом! Попробуй ещё раз:")
        return
    if user_id == message.from_user.id:
        await message.answer("Нельзя обмениваться с самим собой!")
        return
    user = await get_user(user_id)
    if not user:
        await message.answer(
            f"Пользователь с ID {user_id} не найден в базе бота.\n"
            f"Возможные причины:\n"
            f"- Пользователь ещё не запускал бота (не нажал /start)\n"
            f"- ID написан с ошибкой\n"
            f"Попроси друга написать боту /start, а затем попробуй снова!\n"
            f"Или используй /trades для возврата:"
        )
        return
    await state.update_data(trade_to_user=user_id, trade_to_username=user[1] or str(user_id))
    await message.answer(
        f"Игрок найден: ID {user_id} (@{user[1] or 'без username'})\n"
        f"Теперь введи номер карточки, которую ты хочешь ОТДАТЬ:\n"
        f"Посмотри свою коллекцию: /mycards",
        reply_markup=back_to_menu_keyboard()
    )
    await state.set_state(UserStates.waiting_for_trade_from_card)


@dp.message(UserStates.waiting_for_trade_from_card)
async def process_trade_from_card(message: types.Message, state: FSMContext):
    try:
        from_card_id = int(message.text)
    except ValueError:
        await message.answer("Номер должен быть числом. Попробуй ещё раз:")
        return
    count = await get_user_card_count(message.from_user.id, from_card_id)
    if count <= 0:
        await message.answer("У тебя нет такой карточки! Проверь коллекцию: /mycards")
        return
    card = await get_card_by_id(from_card_id)
    if not card:
        await message.answer("Карточка не найдена!")
        return
    await state.update_data(trade_from_card=from_card_id)
    await message.answer(
        f"Ты отдаёшь: {card[1]} ({get_rarity_color(card[4])} {card[4].capitalize()})\n"
        f"Теперь введи номер карточки, которую ты хочешь ПОЛУЧИТЬ:",
        reply_markup=back_to_menu_keyboard()
    )
    await state.set_state(UserStates.waiting_for_trade_to_card)


@dp.message(UserStates.waiting_for_trade_to_card)
async def process_trade_to_card(message: types.Message, state: FSMContext):
    try:
        to_card_id = int(message.text)
    except ValueError:
        await message.answer("Номер должен быть числом. Попробуй ещё раз:")
        return
    data = await state.get_data()
    to_user_id = data.get('trade_to_user')
    from_card_id = data.get('trade_from_card')
    count = await get_user_card_count(to_user_id, to_card_id)
    if count <= 0:
        await message.answer("У этого игрока нет такой карточки! Попробуй другую:")
        return
    to_card = await get_card_by_id(to_card_id)
    from_card = await get_card_by_id(from_card_id)
    if not to_card or not from_card:
        await message.answer("Одна из карточек не найдена!")
        await state.clear()
        return
    offer_id, error = await create_trade_offer(
        message.from_user.id, to_user_id, from_card_id, to_card_id
    )
    if not offer_id:
        await message.answer(error)
        await state.clear()
        return
    try:
        await bot.send_message(
            to_user_id,
            f"Новое предложение обмена!\n"
            f"От: @{message.from_user.username or message.from_user.first_name}\n"
            f"Даёт: {from_card[1]} ({get_rarity_color(from_card[4])})\n"
            f"Просит: {to_card[1]} ({get_rarity_color(to_card[4])})\n"
            f"Открой /trades и нажми 'Входящие предложения' чтобы принять или отклонить."
        )
    except Exception as e:
        logger.info(f"Не удалось уведомить пользователя {to_user_id}: {e}")
    await message.answer(
        f"Предложение обмена создано!\n"
        f"Номер: {offer_id}\n"
        f"Игрок: @{data.get('trade_to_username')}\n"
        f"Ты отдаёшь: {from_card[1]} ({get_rarity_color(from_card[4])})\n"
        f"Ты получишь: {to_card[1]} ({get_rarity_color(to_card[4])})\n"
        f"Предложение действительно 24 часа.\n"
        f"Игрок получит уведомление.",
        reply_markup=back_to_menu_keyboard()
    )
    await state.clear()


@dp.callback_query(lambda c: c.data.startswith("trade_view_"))
async def trade_view(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        offer_id = int(callback.data.replace("trade_view_", ""))
    except ValueError:
        await callback.message.answer("Неверный номер предложения")
        return
    offer = await get_trade_offer(offer_id)
    if not offer:
        await callback.message.edit_text("Предложение не найдено.", reply_markup=back_to_menu_keyboard())
        return
    offer_id_db = offer[0]
    from_user = offer[1]
    to_user = offer[2]
    from_card = offer[3]
    to_card = offer[4]
    status = offer[5]
    expires_at = offer[7] if len(offer) > 7 else None
    from_card_info = await get_card_by_id(from_card)
    to_card_info = await get_card_by_id(to_card)
    from_user_data = await get_user(from_user)
    to_user_data = await get_user(to_user)
    from_username = from_user_data[1] if from_user_data else 'Unknown'
    to_username = to_user_data[1] if to_user_data else 'Unknown'
    is_recipient = (to_user == callback.from_user.id)
    text = f"Предложение обмена {offer_id}\n"
    text += f"Статус: {status}\n"
    text += f"От: @{from_username}\n"
    text += f"Для: @{to_username}\n"
    if from_card_info:
        text += f"Отдаёт: {from_card_info[1]}\n"
        text += f"   {get_rarity_color(from_card_info[4])} {from_card_info[4].capitalize()}\n"
        text += f"   Художник: {from_card_info[2]}\n"
    if to_card_info:
        text += f"Получает: {to_card_info[1]}\n"
        text += f"   {get_rarity_color(to_card_info[4])} {to_card_info[4].capitalize()}\n"
        text += f"   Художник: {to_card_info[2]}\n"
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at)
            text += f"Действует до: {expires_dt.strftime('%d.%m.%Y %H:%M')}\n"
        except:
            pass
    keyboard = trade_offer_keyboard(offer_id, callback.from_user.id, is_recipient)
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("trade_accept_"))
async def trade_accept(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        offer_id = int(callback.data.replace("trade_accept_", ""))
    except ValueError:
        await callback.message.answer("Неверный номер")
        return
    success, msg = await accept_trade_offer(offer_id, callback.from_user.id)
    await callback.message.edit_text(msg, reply_markup=back_to_menu_keyboard())
    if success:
        offer = await get_trade_offer(offer_id)
        if offer:
            from_user = offer[1]
            try:
                await bot.send_message(from_user,
                                       f"Твоё предложение обмена {offer_id} было принято!\n"
                                       f"Проверь коллекцию: /collection")
            except:
                pass
        completed_tasks = await update_task_progress(callback.from_user.id, "trade")
        if completed_tasks:
            await asyncio.sleep(1)
            for task in completed_tasks:
                await safe_send(callback.message,
                                f"Задание выполнено!\n"
                                f"{task['name']}\n"
                                f"Награда: +{task['reward']} монет")
        new_achievements = await check_and_award_achievements(callback.from_user.id)
        if new_achievements:
            await asyncio.sleep(1)
            for ach in new_achievements:
                await send_sticker(callback.message, "achievement")
                await safe_send(callback.message,
                                f"Новое достижение!\n{ach['name']}\n{ach['description']}\n+{ach['reward']} монет")


@dp.callback_query(lambda c: c.data.startswith("trade_decline_"))
async def trade_decline(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        offer_id = int(callback.data.replace("trade_decline_", ""))
    except ValueError:
        await callback.message.answer("Неверный номер")
        return
    success, msg = await decline_trade_offer(offer_id, callback.from_user.id)
    await callback.message.edit_text(msg, reply_markup=back_to_menu_keyboard())
    if success:
        offer = await get_trade_offer(offer_id)
        if offer:
            from_user = offer[1]
            try:
                await bot.send_message(from_user,
                                       f"Твоё предложение обмена {offer_id} было отклонено.")
            except:
                pass


@dp.callback_query(lambda c: c.data.startswith("trade_cancel_"))
async def trade_cancel(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        offer_id = int(callback.data.replace("trade_cancel_", ""))
    except ValueError:
        await callback.message.answer("Неверный номер")
        return
    success, msg = await cancel_trade_offer(offer_id, callback.from_user.id)
    await callback.message.edit_text(msg, reply_markup=back_to_menu_keyboard())


# ============================================
# ПОИСК И ПРОСМОТР (без изменений)
# ============================================
@dp.message(Command("search"))
@dp.callback_query(lambda c: c.data == "search_category")
async def search_by_category(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        await callback.answer()
    else:
        message = callback
    categories = await get_all_categories()
    if not categories:
        await safe_send(message, "Нет категорий.", reply_markup=back_to_menu_keyboard())
        return
    await safe_send(message, "Выбери категорию:", reply_markup=category_filter_keyboard(categories))


@dp.callback_query(lambda c: c.data.startswith("category_"))
async def show_category_cards(callback: types.CallbackQuery):
    category = callback.data.replace("category_", "")
    cards = await get_cards_by_category(category)
    if not cards:
        await safe_send(callback.message, f"В категории '{category}' нет карточек.",
                        reply_markup=back_to_menu_keyboard())
        await callback.answer()
        return
    cards_text = f"Категория '{category}':\n"
    for card in cards:
        card_id = card[0]
        name = card[1]
        artist = card[2]
        rarity = card[4]
        color = get_rarity_color(rarity)
        cards_text += f"{color} {name} - {artist}\n"
    await safe_send(callback.message, cards_text, reply_markup=back_to_menu_keyboard())
    await callback.answer()


@dp.callback_query(lambda c: c.data == "artists_list")
async def artists_list(callback: types.CallbackQuery):
    artists = await get_all_artists()
    if not artists:
        await safe_send(callback.message, "Художники пока не добавлены.", reply_markup=back_to_menu_keyboard())
        await callback.answer()
        return
    text = "Список художников:\n"
    for i, artist in enumerate(artists, 1):
        text += f"{i}. {artist}\n"
    await safe_send(callback.message, text, reply_markup=back_to_menu_keyboard())
    await callback.answer()


@dp.message(Command("view"))
async def view_collection(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "Просмотр коллекции\n"
            "Использование:\n"
            "/view номер_пользователя - по номеру\n"
            "/view @username - по username\n"
            "Пример: /view 123456789 или /view @username"
        )
        return
    target = args[1].strip()
    if target.startswith('@'):
        username = target[1:]
        user_id = await get_user_by_username(username)
        if not user_id:
            await message.answer(f"Пользователь @{username} не найден в базе бота.")
            return
    else:
        try:
            user_id = int(target)
        except ValueError:
            await message.answer("Неверный формат. Используй номер (число) или @username")
            return
    user = await get_user(user_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return
    username = user[1] or "Без имени"
    coins = user[2]
    trades = user[5]
    collection = await get_user_collection(user_id)
    stats = await get_collection_stats(user_id)
    await update_task_progress(message.from_user.id, "view")
    if not collection:
        await message.answer(f"Коллекция @{username}\nКоллекция пуста\nМонеты: {coins}\nОбменов: {trades}")
        return
    by_rarity = {"mythical": [], "secret": [], "legendary": [], "epic": [], "rare": [], "common": []}
    for card in collection:
        card_id = card[0]
        count = card[1]
        name = card[2]
        artist = card[3]
        rarity = card[4]
        category = card[6]
        if rarity in by_rarity:
            by_rarity[rarity].append((card_id, count, name, artist, category))
    completion = (stats["unique"] / stats["total_in_game"] * 100) if stats["total_in_game"] > 0 else 0
    collection_text = f"Коллекция @{username}\n"
    collection_text += f"Уникальных: {stats['unique']} из {stats['total_in_game']} ({completion:.1f}%)\n"
    collection_text += f"Монеты: {coins}\n"
    collection_text += f"Обменов: {trades}\n"
    for rarity in ["mythical", "secret", "legendary", "epic", "rare", "common"]:
        if by_rarity[rarity]:
            color = get_rarity_color(rarity)
            collection_text += f"{color} {rarity.capitalize()} ({len(by_rarity[rarity])})\n"
            for card_id, count, name, artist, category in by_rarity[rarity]:
                dup = f" x{count}" if count > 1 else ""
                collection_text += f"- {name} - {artist} [{category}]{dup}\n"
    collection_text += "\n"
    await message.answer(collection_text)


@dp.message(Command("achievements"))
@dp.callback_query(lambda c: c.data == "achievements")
async def show_achievements(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    obtained = await get_user_achievements(user_id)
    obtained_keys = [a[0] for a in obtained]
    total = len(ACHIEVEMENTS)
    got = len(obtained_keys)
    text = f"Твои достижения\n"
    text += f"Получено: {got} из {total}\n"
    if obtained_keys:
        text += "Полученные:\n"
        for key in obtained_keys:
            if key in ACHIEVEMENTS:
                ach = ACHIEVEMENTS[key]
                text += f"{ach['name']}\n"
                text += f"  {ach['description']}\n"
                text += f"  Награда: +{ach['reward']} монет\n"
    remaining = [k for k in ACHIEVEMENTS.keys() if k not in obtained_keys]
    if remaining:
        text += "Ещё не получены:\n"
        for key in remaining:
            ach = ACHIEVEMENTS[key]
            text += f"{ach['name']}\n"
            text += f"  {ach['description']}\n"
    await safe_send(message, text, reply_markup=back_to_menu_keyboard())


@dp.message(Command("help"))
@dp.callback_query(lambda c: c.data == "help")
async def show_help(update):
    if isinstance(update, types.CallbackQuery):
        message = update.message
        await update.answer()
    else:
        message = update
    help_text = (
        "Команды бота:\n"
        "Основные:\n"
        "/start - Запустить бота\n"
        "/claim - Получить карточку\n"
        "/mycards - Моя коллекция с номерами\n"
        "/card номер - Инфо о карточке\n"
        "/collection - Моя коллекция\n"
        "/stats - Статистика\n"
        "/wallet - Кошелёк\n"
        "/daily - Ежедневный бонус\n"
        "/tasks - Ежедневные задания\n"
        "/streak - Серия дней\n"
        "/shop - Магазин\n"
        "/inventory - Инвентарь\n"
        "/market - Рынок (фикс. цена)\n"
        "/auction - Аукционы (ставки)\n"
        "/sell номер цена - Продать на рынке\n"
        "/bid номер сумма - Сделать ставку\n"
        "/ref - Моя реферальная ссылка\n"
        "/leaderboard - Рейтинг\n"
        "/achievements - Достижения\n"
        "/trades - Обмены\n"
        "/search - Поиск по категории\n"
        "/view номер или @username - Просмотр чужой коллекции\n"
        "Новые команды:\n"
        "/expedition - Экспедиция (раз в 12 часов)\n"
        "/premium - Premium подписка (49 Stars/мес)\n"
        "/gift - Подарки другим игрокам\n"
        f"Карточка каждые {CARD_COOLDOWN_HOURS} часа (админам без ожидания)\n"
        "Редкости:\n"
        "⚪ Common - 49.99%\n"
        "🔵 Rare - 25%\n"
        "🟣 Epic - 15%\n"
        "🟡 Legendary - 9%\n"
        "🔴 Secret - 1%\n"
        "🟣✨ Mythical - 0.01% (почти невозможно!)\n"
        "Техническая поддержка:\n"
        "Если нужна помощь, обратись в канал:\n"
        "@azraBotka"
    )
    await safe_send(message, help_text, reply_markup=back_to_menu_keyboard())


@dp.callback_query(lambda c: c.data == "main_menu")
async def process_main_menu(callback: types.CallbackQuery):
    await safe_send(callback.message, "Главное меню", reply_markup=main_menu_keyboard())
    await callback.answer()


# ============================================
# ЭКСПЕДИЦИЯ (без изменений)
# ============================================
@dp.message(Command("expedition"))
@dp.callback_query(lambda c: c.data == "expedition")
async def expedition_command(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    if await check_blocked(user_id):
        await safe_send(message, "Ты заблокирован.")
        return
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    is_ready, seconds_left = await check_expedition_cooldown(user_id)
    if not is_ready:
        cooldown_text = format_seconds(seconds_left)
        await safe_send(message,
                        f"🗺️ Экспедиция\n"
                        f"Ты недавно был в экспедиции!\n"
                        f"Следующая экспедиция через: {cooldown_text}",
                        reply_markup=expedition_keyboard(False, cooldown_text))
        return
    await safe_send(message,
                    f"🗺️ Экспедиция\n"
                    f"Отправься в путешествие и найди:\n"
                    f"💰 Клады с монетами и карточками\n"
                    f"🏪 Торговца со скидками\n"
                    f"✨ Уникальные карточки\n"
                    f"Кулдаун: {EXPEDITION_COOLDOWN_HOURS} часов\n"
                    f"{'💎 Premium: 3 часа' if not await is_premium(user_id) else '✅ Premium активен: 3 часа'}\n"
                    f"{'👑 Админ: без ожидания' if is_admin(user_id) else ''}",
                    reply_markup=expedition_keyboard(True))


@dp.callback_query(lambda c: c.data == "expedition_start")
async def expedition_start(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    user_id = callback.from_user.id
    is_ready, seconds_left = await check_expedition_cooldown(user_id)
    if not is_ready:
        await callback.message.answer(
            f"⏳ Экспедиция недоступна!\n"
            f"Следующая через: {format_seconds(seconds_left)}",
            reply_markup=expedition_keyboard(False, format_seconds(seconds_left)))
        return
    roll = random.uniform(0, 100)
    cumulative = 0
    event = "nothing"
    for event_key, chance in EXPEDITION_CHANCES.items():
        cumulative += chance
        if roll <= cumulative:
            event = event_key
            break
    await update_expedition(user_id)
    if event == "walk":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_card_time = datetime('now', '-20 minutes') WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await callback.message.answer(
            "🚶‍♂️ Прогулка\n"
            "Ты просто прогулялся по парку. Ничего интересного, но кулдаун на карточку снижен на 20 минут!",
            reply_markup=expedition_result_keyboard())
    elif event == "treasure":
        coins_found = random.randint(TREASURE_REWARDS["coins_min"], TREASURE_REWARDS["coins_max"])
        cards_found = random.randint(TREASURE_REWARDS["cards_min"], TREASURE_REWARDS["cards_max"])
        case_found = random.randint(TREASURE_REWARDS["case_or_bundle_min"], TREASURE_REWARDS["case_or_bundle_max"])
        skip_found = random.randint(TREASURE_REWARDS["skip_min"], TREASURE_REWARDS["skip_max"])
        if coins_found > 0:
            await update_coins(user_id, coins_found)
        cards_text = ""
        if cards_found > 0:
            for _ in range(cards_found):
                rarity = get_random_rarity()
                card = await get_random_card_by_rarity(rarity)
                if card:
                    await add_card_to_collection(user_id, card[0])
                    cards_text += f"{get_rarity_color(card[4])} {card[1]}\n"
        case_text = ""
        if case_found > 0:
            case_type = random.choice(CASE_TYPES_FOR_TREASURE)
            case_info = CASES.get(case_type)
            if case_info:
                await add_item(user_id, case_type, 1)
                case_text = f"📦 {case_info['name']}\n"
        skip_text = ""
        if skip_found > 0:
            await add_item(user_id, "skip", skip_found)
            skip_text = f"⏭️ Пропуск x{skip_found}\n"
        text = f"💰 Клад найден!\n"
        text += f"Монеты: +{coins_found}\n"
        if cards_text:
            text += f"Карточки:\n{cards_text}\n"
        if case_text:
            text += case_text
        if skip_text:
            text += skip_text
        await callback.message.answer(text, reply_markup=expedition_result_keyboard())
    elif event == "merchant":
        offer_roll = random.uniform(0, 100)
        cumulative = 0
        offer_type = "shop_item_discount"
        for offer_key, chance in MERCHANT_OFFERS.items():
            cumulative += chance
            if offer_roll <= cumulative:
                offer_type = offer_key
                break
        if offer_type == "shop_item_discount":
            item_keys = list(SHOP_ITEMS.keys())
            item_key = random.choice(item_keys)
            item = SHOP_ITEMS[item_key]
            discount = random.randint(MERCHANT_DISCOUNT_ITEM_MIN, MERCHANT_DISCOUNT_ITEM_MAX)
            discounted_price = int(item["price"] * (100 - discount) / 100)
            await callback.message.answer(
                f"🏪 Торговец\n"
                f"Ты встретил странствующего торговца!\n"
                f"Он предлагает: {item['name']}\n"
                f"Обычная цена: {item['price']} монет\n"
                f"Скидка: {discount}%\n"
                f"Твоя цена: {discounted_price} монет\n"
                f"Купить?",
                reply_markup=merchant_keyboard(offer_type, item_key, discounted_price, discount))
        elif offer_type == "case_discount":
            case_keys = list(CASES.keys())
            case_key = random.choice(case_keys)
            case = CASES[case_key]
            discounted_price = int(case["price"] * (100 - MERCHANT_DISCOUNT_CASE) / 100)
            await callback.message.answer(
                f"🏪 Торговец\n"
                f"Ты встретил странствующего торговца!\n"
                f"Он предлагает: {case['name']}\n"
                f"Обычная цена: {case['price']} монет\n"
                f"Скидка: {MERCHANT_DISCOUNT_CASE}%\n"
                f"Твоя цена: {discounted_price} монет\n"
                f"Купить?",
                reply_markup=merchant_keyboard(offer_type, case_key, discounted_price, MERCHANT_DISCOUNT_CASE))
        elif offer_type == "premium_stars":
            await callback.message.answer(
                f"🏪 Торговец\n"
                f"Ты встретил странствующего торговца!\n"
                f"Он предлагает эксклюзивное предложение:\n"
                f"⭐ Premium подписка на 1 месяц\n"
                f"Обычная цена: {PREMIUM_PRICE} Stars\n"
                f"Твоя цена: {PREMIUM_PRICE_MERCHANT} Stars\n"
                f"Преимущества Premium:\n"
                f"• x2 монеты за всё\n"
                f"• Без комиссии на рынке\n"
                f"• Безлимитные подарки\n"
                f"• Экспедиция каждые 3 часа",
                reply_markup=merchant_keyboard(offer_type, price=PREMIUM_PRICE_MERCHANT))
    elif event == "tired":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_card_time = datetime('now', '+20 minutes') WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await callback.message.answer(
            "😴 Усталость\n"
            "Ты устал и решил отдохнуть. Кулдаун на карточку увеличен на 20 минут.",
            reply_markup=expedition_result_keyboard())
    elif event == "unique_card":
        rarity = "legendary"
        card = await get_random_card_by_rarity(rarity)
        if card:
            await add_card_to_collection(user_id, card[0])
            rarity_color = get_rarity_color(card[4])
            card_text = (
                f"✨ Уникальная находка!\n"
                f"Ты нашёл редкую карточку:\n"
                f"{rarity_color} {card[1]}\n"
                f"Художник: {card[2]}\n"
                f"Редкость: {rarity_color} {card[4].capitalize()}\n"
                f"Категория: {card[5]}"
            )
            if card[6]:
                card_text += f"\n{card[6]}"
            card_path = os.path.join(CARDS_FOLDER, card[3])
            if os.path.exists(card_path):
                try:
                    photo = FSInputFile(card_path)
                    await callback.message.answer_photo(photo=photo, caption=card_text,
                                                        reply_markup=expedition_result_keyboard())
                except:
                    await callback.message.answer(card_text, reply_markup=expedition_result_keyboard())
            else:
                await callback.message.answer(card_text, reply_markup=expedition_result_keyboard())
        else:
            await callback.message.answer(
                "✨ Уникальная находка!\n"
                "К сожалению, сейчас нет доступных уникальных карточек. Попробуй позже!",
                reply_markup=expedition_result_keyboard())
    elif event == "nothing":
        await callback.message.answer(
            "🌫️ Ничего интересного\n"
            "Ты прошёл по знакомой тропе. Ничего особенного не произошло.",
            reply_markup=expedition_result_keyboard())
    new_achievements = await check_expedition_achievements(user_id)
    if new_achievements:
        await asyncio.sleep(1)
        for ach in new_achievements:
            await send_sticker(callback.message, "achievement")
            reward_text = ""
            if "reward_coins" in ach:
                await update_coins(user_id, ach["reward_coins"])
                reward_text = f"\n+{ach['reward_coins']} монет"
            elif "reward_case" in ach:
                await add_item(user_id, ach["reward_case"], 1)
                case_info = CASES.get(ach["reward_case"])
                if case_info:
                    reward_text = f"\n+{case_info['name']}"
            await safe_send(callback.message,
                           f"Новое достижение!\n{ach['name']}\n{ach['description']}{reward_text}")


@dp.callback_query(lambda c: c.data == "expedition_stats")
async def expedition_stats(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    user_id = callback.from_user.id
    info = await get_expedition_info(user_id)
    count = info["count"]
    obtained = await get_user_achievements(user_id)
    expedition_ach_count = sum(1 for a in obtained if a[0].startswith("expedition_"))
    await callback.message.answer(
        f"📊 Статистика экспедиций\n"
        f"Всего экспедиций: {count}\n"
        f"Достижений за экспедиции: {expedition_ach_count}\n"
        f"Следующее достижение:",
        reply_markup=expedition_stats_keyboard(count, expedition_ach_count))


# ============================================
# ТОРГОВЕЦ (исправлен - теперь выдаёт товары)
# ============================================
@dp.callback_query(lambda c: c.data.startswith("merchant_buy_item_"))
async def merchant_buy_item(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        parts = callback.data.replace("merchant_buy_item_", "").split("_")
        item_key = parts[0]
        price = int(parts[1])
    except (ValueError, IndexError):
        await callback.message.answer("Ошибка! Попробуй ещё раз.")
        return
    user_coins = await get_user_coins(callback.from_user.id)
    if user_coins < price:
        await callback.message.answer(f"Недостаточно монет! Нужно {price}, у тебя {user_coins}")
        return
    await update_coins(callback.from_user.id, -price)
    await add_item(callback.from_user.id, item_key, 1)
    item = SHOP_ITEMS.get(item_key)
    item_name = item['name'] if item else item_key
    await callback.message.answer(
        f"✅ Ты купил {item_name} у торговца!\n\n"
        f"💰 Списано: {price} монет\n"
        f"📦 Предмет добавлен в инвентарь.",
        reply_markup=expedition_result_keyboard()
    )


@dp.callback_query(lambda c: c.data.startswith("merchant_buy_case_"))
async def merchant_buy_case(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        parts = callback.data.replace("merchant_buy_case_", "").split("_")
        case_key = parts[0]
        price = int(parts[1])
    except (ValueError, IndexError):
        await callback.message.answer("Ошибка! Попробуй ещё раз.")
        return
    user_coins = await get_user_coins(callback.from_user.id)
    if user_coins < price:
        await callback.message.answer(f"Недостаточно монет! Нужно {price}, у тебя {user_coins}")
        return
    await update_coins(callback.from_user.id, -price)
    result, error = await open_case(callback.from_user.id, case_key)
    if error:
        await update_coins(callback.from_user.id, price)
        await callback.message.answer(f"Ошибка: {error}")
        return
    cards = result.get("cards", [])
    items = result.get("items", [])
    text = f"🎉 Ты купил кейс у торговца!\n\n"
    if cards:
        text += f"🎴 Полученные карточки:\n"
        for card in cards:
            card_id = card[0]
            name = card[1]
            rarity = card[4]
            color = get_rarity_color(rarity)
            text += f"  {color} {name} (#{card_id})\n"
        text += "\n"
    if items:
        text += f"📦 Полученные предметы:\n"
        for item_key in items:
            item = SHOP_ITEMS.get(item_key)
            if item:
                text += f"  • {item['name']}\n"
        text += "\n"
    if not cards and not items:
        text += "Кейс был пустой! Попробуй ещё раз.\n"
    text += f"💰 Списано: {price} монет"
    await callback.message.answer(text, reply_markup=expedition_result_keyboard())


# ============================================
# ТОРГОВЕЦ: PREMIUM (исправлен - теперь через инвойс)
# ============================================
@dp.callback_query(lambda c: c.data.startswith("merchant_buy_premium_"))
async def merchant_buy_premium(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        price = int(callback.data.replace("merchant_buy_premium_", ""))
    except:
        await callback.message.answer("Ошибка!")
        return
    # Создаём инвойс с Stars
    prices = [LabeledPrice(label=f"Premium (у торговца)", amount=price)]
    try:
        await callback.message.answer_invoice(
            title="Premium подписка (у торговца)",
            description=f"Premium на {PREMIUM_DURATION} дней со скидкой торговца",
            prices=prices,
            provider_token="",
            payload=f"premium_merchant_{callback.from_user.id}",
            currency="XTR"
        )
    except Exception as e:
        logger.error(f"Ошибка создания инвойса торговца: {e}")
        await callback.message.answer("Ошибка при создании платежа. Попробуй позже.")


# ============================================
# PREMIUM (исправлен - добавлена покупка со скидкой)
# ============================================
@dp.message(Command("premium"))
@dp.callback_query(lambda c: c.data == "premium_menu")
async def premium_menu(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    if await check_blocked(user_id):
        await safe_send(message, "Ты заблокирован.")
        return
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    premium_status = await get_premium_status(user_id)
    if premium_status["is_premium"]:
        if premium_status["is_admin"]:
            days_text = "∞ (Админ)"
        else:
            days_text = f"{premium_status['days_left']} дн."
        text = (
            f"⭐ Premium подписка\n"
            f"✅ Статус: Активен\n"
            f"📅 Осталось: {days_text}\n"
            f"Твои преимущества:\n"
            f"• x2 монеты за всё\n"
            f"• Без комиссии на рынке и аукционах\n"
            f"• Безлимитные подарки (без 48ч кулдауна)\n"
            f"• Безлимитная продажа на рынке\n"
            f"• Экспедиция каждые 3 часа (вместо 12)\n"
            f"• Торговец продаёт Premium за 19 Stars"
        )
        await safe_send(message, text, reply_markup=premium_menu_keyboard(True, premium_status["days_left"]))
    else:
        text = (
            f"⭐ Premium подписка\n"
            f"Получи доступ к эксклюзивным преимуществам!\n"
            f"Преимущества Premium:\n"
            f"• x2 монеты за всё\n"
            f"• Без комиссии на рынке и аукционах\n"
            f"• Безлимитные подарки (без 48ч кулдауна)\n"
            f"• Безлимитная продажа на рынке\n"
            f"• Экспедиция каждые 3 часа (вместо 12)\n"
            f"• Торговец продаёт Premium за 19 Stars\n"
            f"Цена: {PREMIUM_PRICE} Stars/месяц"
        )
        await safe_send(message, text, reply_markup=premium_menu_keyboard(False))


@dp.callback_query(lambda c: c.data == "premium_buy")
async def premium_buy(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    await callback.message.edit_text(
        f"⭐ Оформление Premium\n"
        f"Цена: {PREMIUM_PRICE} Stars\n"
        f"Длительность: {PREMIUM_DURATION} дней\n"
        f"Нажми кнопку для оплаты:",
        reply_markup=premium_buy_keyboard())


@dp.callback_query(lambda c: c.data == "premium_confirm_buy")
async def premium_confirm_buy(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    prices = [LabeledPrice(label="Premium подписка", amount=PREMIUM_PRICE)]
    try:
        await callback.message.answer_invoice(
            title="Premium подписка",
            description=f"Premium на {PREMIUM_DURATION} дней",
            prices=prices,
            provider_token="",
            payload=f"premium_{callback.from_user.id}",
            currency="XTR"
        )
    except Exception as e:
        logger.error(f"Ошибка создания инвойса: {e}")
        await callback.message.answer("Ошибка при создании платежа. Попробуй позже.")


@dp.callback_query(lambda c: c.data == "premium_buy_discounted")
async def premium_buy_discounted(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    data = await state.get_data()
    discount = data.get('premium_discount', 0)
    if discount <= 0:
        await callback.message.answer("❌ Скидка не найдена. Активируй промокод ещё раз.")
        return
    final_price = int(PREMIUM_PRICE * (100 - discount) / 100)
    prices = [LabeledPrice(label=f"Premium (-{discount}%)", amount=final_price)]
    try:
        await callback.message.answer_invoice(
            title="Premium подписка",
            description=f"Premium на {PREMIUM_DURATION} дней (скидка {discount}%)",
            prices=prices,
            provider_token="",
            payload=f"premium_discounted_{callback.from_user.id}",
            currency="XTR"
        )
    except Exception as e:
        logger.error(f"Ошибка создания инвойса со скидкой: {e}")
        await callback.message.answer("Ошибка при создании платежа. Попробуй позже.")


@dp.pre_checkout_query(lambda query: True)
async def pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@dp.message(F.successful_payment)
async def successful_payment(message: types.Message, state: FSMContext):
    if not message.from_user:
        return
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload
    if payload.startswith("premium_"):
        await set_premium(user_id, PREMIUM_DURATION)
        await state.clear()
        await message.answer(
            f"⭐ Premium активирован!\n"
            f"Спасибо за покупку!\n"
            f"Длительность: {PREMIUM_DURATION} дней\n"
            f"Твои преимущества уже работают:\n"
            f"• x2 монеты за всё\n"
            f"• Без комиссии на рынке\n"
            f"• Безлимитные подарки\n"
            f"• Экспедиция каждые 3 часа",
            reply_markup=main_menu_keyboard())


@dp.callback_query(lambda c: c.data == "premium_benefits")
async def premium_benefits(callback: types.CallbackQuery):
    if not callback.from_user:
        return
    await callback.answer()
    text = (
        "⭐ Преимущества Premium\n"
        "💰 x2 монеты за всё\n"
        "   Все монеты за карточки, задания, ежедневный бонус удваиваются\n"
        "🏪 Без комиссии на рынке\n"
        "   Продавай карточки без 10% комиссии\n"
        "🔨 Без комиссии на аукционах\n"
        "   Участвуй в аукционах без комиссии\n"
        "🎁 Безлимитные подарки\n"
        "   Отправляй подарки без 48-часового кулдауна\n"
        "🏪 Безлимитная продажа\n"
        "   Выставляй неограниченное количество карточек на рынок\n"
        "🗺️ Экспедиция каждые 3 часа\n"
        "   Вместо 12 часов для обычных пользователей"
    )
    await callback.message.edit_text(text, reply_markup=premium_benefits_keyboard())


# ============================================
# ПОДАРКИ (полная система - убраны дубликаты)
# ============================================
@dp.message(Command("gift"))
@dp.callback_query(lambda c: c.data == "gift_menu")
async def gift_menu(callback):
    if isinstance(callback, types.CallbackQuery):
        message = callback.message
        user_id = callback.from_user.id
        await callback.answer()
    else:
        message = callback
        user_id = callback.from_user.id
    if await check_blocked(user_id):
        await safe_send(message, "Ты заблокирован.")
        return
    user = await get_user(user_id)
    if not user:
        await safe_send(message, "Сначала запусти бота командой /start")
        return
    is_ready, seconds_left = await check_gift_cooldown(user_id)
    if not is_ready:
        cooldown_text = format_seconds(seconds_left)
        await safe_send(message,
                        f"🎁 Подарки\n"
                        f"Ты недавно отправлял подарок!\n"
                        f"Следующий подарок через: {cooldown_text}\n"
                        f"💎 Premium пользователи могут отправлять подарки без ограничений",
                        reply_markup=gift_menu_keyboard(False, cooldown_text))
        return
    await safe_send(message,
                    f"🎁 Подарки\n"
                    f"Собери подарочный набор и отправь его другому игроку!\n"
                    f"В набор можно положить:\n"
                    f"• Монеты\n"
                    f"• Карточки\n"
                    f"• Предметы из инвентаря\n"
                    f"• Личное сообщение\n"
                    f"Кулдаун: {GIFT_COOLDOWN_HOURS} часов\n"
                    f"{'💎 Premium: без ограничений' if not await is_premium(user_id) else '✅ Premium активен: без ограничений'}",
                    reply_markup=gift_menu_keyboard(True))


@dp.callback_query(lambda c: c.data == "gift_create")
async def gift_create(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    user_id = callback.from_user.id
    await state.set_data({})
    items = await get_user_items(user_id)
    coins = await get_user_coins(user_id)
    collection = await get_user_collection(user_id)
    text = f"📦 Сборка подарочного набора\n"
    text += f"Твой инвентарь:\n"
    text += f"💰 Монеты: {coins}\n"
    text += f"📦 Предметы: {len(items)}\n"
    text += f"🎴 Карточки: {len(collection)}\n"
    text += f"Выбери, что добавить в подарок:"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Добавить монеты", callback_data="gift_add_coins")],
        [InlineKeyboardButton(text="🎴 Добавить карточку", callback_data="gift_add_card")],
        [InlineKeyboardButton(text="📦 Добавить предмет", callback_data="gift_add_item_menu")],
        [InlineKeyboardButton(text="✅ Завершить набор", callback_data="gift_finish")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="gift_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data == "gift_add_coins")
async def gift_add_coins(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    await callback.message.edit_text("💰 Введи количество монет для подарка:")
    await state.set_state(UserStates.waiting_for_gift_coins)


@dp.message(UserStates.waiting_for_gift_coins)
async def process_gift_coins(message: types.Message, state: FSMContext):
    try:
        coins = int(message.text)
    except ValueError:
        await message.answer("Введи число!")
        return
    user_coins = await get_user_coins(message.from_user.id)
    if coins > user_coins:
        await message.answer(f"У тебя только {user_coins} монет!")
        return
    data = await state.get_data()
    data['gift_coins'] = coins
    await state.set_data(data)
    await state.clear()
    await show_gift_create_menu(message, state)


@dp.callback_query(lambda c: c.data == "gift_add_card")
async def gift_add_card(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    await callback.message.edit_text("🎴 Введи номер карточки для подарка:")
    await state.set_state(UserStates.waiting_for_gift_card)


@dp.message(UserStates.waiting_for_gift_card)
async def process_gift_card(message: types.Message, state: FSMContext):
    try:
        card_id = int(message.text)
    except ValueError:
        await message.answer("Введи номер карточки!")
        return
    count = await get_user_card_count(message.from_user.id, card_id)
    if count <= 0:
        await message.answer("У тебя нет такой карточки!")
        return
    data = await state.get_data()
    if 'gift_cards' not in data:
        data['gift_cards'] = []
    data['gift_cards'].append(card_id)
    await state.set_data(data)
    await state.clear()
    await message.answer(f"✅ Карточка #{card_id} добавлена в подарок!")
    await show_gift_create_menu(message, state)


@dp.callback_query(lambda c: c.data == "gift_add_item_menu")
async def gift_add_item_menu(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    items = await get_user_items(callback.from_user.id)
    if not items:
        await callback.message.answer(
            "📦 У тебя нет предметов в инвентаре!\n"
            "Купи предметы в магазине: /shop",
            reply_markup=back_to_menu_keyboard()
        )
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for item_key, quantity in items.items():
        item = SHOP_ITEMS.get(item_key)
        if item:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(
                    text=f"{item['name']} x{quantity}",
                    callback_data=f"gift_add_item_{item_key}"
                )
            ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="gift_create")
    ])
    await callback.message.edit_text(
        "📦 Выбери предмет для добавления в подарок:",
        reply_markup=keyboard
    )


@dp.callback_query(lambda c: c.data.startswith("gift_add_item_"))
async def gift_add_item(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    item_key = callback.data.replace("gift_add_item_", "")
    quantity = await get_item_quantity(callback.from_user.id, item_key)
    if quantity <= 0:
        await callback.message.answer("У тебя нет этого предмета!")
        return
    data = await state.get_data()
    if 'gift_items' not in data:
        data['gift_items'] = {}
    if item_key in data['gift_items']:
        data['gift_items'][item_key] += 1
    else:
        data['gift_items'][item_key] = 1
    await state.set_data(data)
    item = SHOP_ITEMS.get(item_key)
    await callback.message.answer(f"✅ {item['name']} добавлен в подарок!")
    await show_gift_create_menu(callback.message, state)


@dp.callback_query(lambda c: c.data == "gift_finish")
async def gift_finish(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    data = await state.get_data()
    coins = data.get('gift_coins', 0)
    cards = data.get('gift_cards', [])
    items = data.get('gift_items', {})
    if coins == 0 and not cards and not items:
        await callback.message.answer(
            "📦 Подарок пуст!\n"
            "Добавь хотя бы что-то в подарок.",
            reply_markup=back_to_menu_keyboard()
        )
        return
    text = f"📦 Состав подарка:\n"
    if coins > 0:
        text += f"💰 Монеты: {coins}\n"
    if cards:
        text += f"🎴 Карточки: {len(cards)} шт.\n"
    if items:
        text += f"📦 Предметы:\n"
        for item_key, qty in items.items():
            item = SHOP_ITEMS.get(item_key)
            if item:
                text += f"  • {item['name']} x{qty}\n"
    text += f"\nВыбери получателя:"
    all_users = await get_all_users()
    users_list = [(u[0], u[1]) for u in all_users if u[0] != callback.from_user.id and not u[6]]
    if not users_list:
        await callback.message.answer("Нет доступных пользователей!")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for user_id, username in users_list[:10]:
        display_name = f"@{username}" if username else f"ID: {user_id}"
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=display_name, callback_data=f"gift_send_to_{user_id}")
        ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="gift_create")
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data.startswith("gift_send_to_"))
async def gift_send_to(callback: types.CallbackQuery, state: FSMContext):
    if not callback.from_user:
        return
    await callback.answer()
    try:
        receiver_id = int(callback.data.replace("gift_send_to_", ""))
    except ValueError:
        await callback.message.answer("Ошибка!")
        return
    data = await state.get_data()
    coins = data.get('gift_coins', 0)
    card_ids = data.get('gift_cards', [])
    items = data.get('gift_items', {})
    # Списываем монеты у отправителя
    if coins > 0:
        sender_coins = await get_user_coins(callback.from_user.id)
        if sender_coins < coins:
            await callback.message.answer("❌ Недостаточно монет для подарка!")
            return
        await update_coins(callback.from_user.id, -coins)
        await update_coins(receiver_id, coins)
    # Передаём карточки
    for card_id in card_ids:
        count = await get_user_card_count(callback.from_user.id, card_id)
        if count <= 0:
            await callback.message.answer(f"❌ Карточка #{card_id} больше не доступна!")
            return
        await remove_card_from_collection(callback.from_user.id, card_id)
        await add_card_to_collection(receiver_id, card_id)
    # Передаём предметы
    for item_key, quantity in items.items():
        current_qty = await get_item_quantity(callback.from_user.id, item_key)
        if current_qty < quantity:
            await callback.message.answer(f"❌ Предмет {item_key} больше не доступен в нужном количестве!")
            return
        await remove_item(callback.from_user.id, item_key, quantity)
        await add_item(receiver_id, item_key, quantity)
    # Обновляем время последнего подарка
    await update_last_gift_time(callback.from_user.id)
    # Уведомляем получателя
    try:
        gift_text = f"🎁 Ты получил подарок!\n"
        if coins > 0:
            gift_text += f"💰 Монеты: +{coins}\n"
        if card_ids:
            gift_text += f"🎴 Карточки: {len(card_ids)} шт.\n"
        if items:
            gift_text += f"📦 Предметы:\n"
            for item_key, qty in items.items():
                item = SHOP_ITEMS.get(item_key)
                if item:
                    gift_text += f"  • {item['name']} x{qty}\n"
        await bot.send_message(receiver_id, gift_text)
    except:
        pass
    await callback.message.edit_text(f"✅ Подарок отправлен пользователю {receiver_id}!")
    await state.clear()


async def show_gift_create_menu(message, state: FSMContext):
    data = await state.get_data()
    coins = data.get('gift_coins', 0)
    cards = data.get('gift_cards', [])
    items = data.get('gift_items', {})
    text = f"📦 Сборка подарочного набора\n"
    text += f"Текущий состав:\n"
    if coins > 0:
        text += f"💰 Монеты: {coins}\n"
    if cards:
        text += f"🎴 Карточки: {len(cards)} шт.\n"
    if items:
        text += f"📦 Предметы:\n"
        for item_key, qty in items.items():
            item = SHOP_ITEMS.get(item_key)
            if item:
                text += f"  • {item['name']} x{qty}\n"
    if coins == 0 and not cards and not items:
        text += f"\nПодарок пуст. Добавь что-нибудь!"
    else:
        text += f"\nЧто еще добавить?"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Добавить монеты", callback_data="gift_add_coins")],
        [InlineKeyboardButton(text="🎴 Добавить карточку", callback_data="gift_add_card")],
        [InlineKeyboardButton(text="📦 Добавить предмет", callback_data="gift_add_item_menu")],
        [InlineKeyboardButton(text="✅ Завершить набор", callback_data="gift_finish")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="gift_menu")]
    ])
    await message.answer(text, reply_markup=keyboard)


# ============================================
# ЗАПУСК
# ============================================
async def main():
    await init_db()
    await set_bot_commands()
    logging.info("База данных инициализирована")
    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")
