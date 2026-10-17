"""Bilingual Telegram movie catalog bot (Uzbek/Russian), designed for Render."""
from __future__ import annotations

import logging
import os
import secrets
from urllib.parse import urlparse

from dotenv import load_dotenv
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
                      Update, BotCommand)
from telegram.constants import ChatType
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                          ConversationHandler, ContextTypes, MessageHandler, filters)

load_dotenv()  # Load local .env before database.py reads DATABASE_URL.
import database as db
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger("film_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
PAGE_SIZE = 8

TEXTS = {
    "uz": {
        "welcome": "🎬 Film olamiga xush kelibsiz!\n\nKatalogdan film tanlang, nomi bo‘yicha qidiring, janrlarni ko‘ring yoki sevimlilaringizni saqlang.",
        "films": "🎬 Filmlar", "search": "🔎 Qidirish", "genres": "🗂 Janrlar",
        "favorites": "⭐ Sevimlilar", "watched": "🕘 Ko‘rilganlar", "language": "🌐 Til", "help": "ℹ️ Yordam",
        "choose_language": "Tilni tanlang:", "language_changed": "✅ Til o‘zbek tiliga o‘zgartirildi.",
        "ask_search": "Film nomi, aktyor, janr yoki tavsifdan so‘z yuboring. Bekor qilish uchun /cancel_search yozing.",
        "search_cancelled": "Qidiruv bekor qilindi.", "empty": "Hozircha bu bo‘limda filmlar yo‘q.",
        "catalog": "🎬 Film katalogi", "page": "Sahifa", "of": "/", "all_count": "Jami film",
        "details": "🎞 Film haqida", "year": "Yil", "genre": "Janr", "rating": "Reyting",
        "duration": "Davomiyligi", "minutes": "daq.", "no_rating": "ko‘rsatilmagan",
        "favorite_add": "⭐ Sevimlilarga qo‘shish", "favorite_remove": "💛 Sevimlilardan olish",
        "watched_add": "✅ Ko‘rdim deb belgilash", "watched_remove": "↩️ Ko‘rilganlardan olish",
        "watch": "▶️ Tomosha qilish", "play_video": "📺 Botda ko‘rish", "no_source": "ℹ️ Tomosha qilish manbasi hali qo‘shilmagan.",
        "back": "⬅️ Orqaga", "home": "🏠 Menyu", "saved_fav": "Sevimlilar ro‘yxati yangilandi.",
        "saved_watched": "Ko‘rilganlar ro‘yxati yangilandi.", "not_found": "Film topilmadi.",
        "no_genres": "Janrlar hozircha mavjud emas.", "select_genre": "Janrni tanlang:",
        "help_text": "Botdan foydalanish:\n• 🎬 Filmlar — katalogni ochish\n• 🔎 Qidirish — nom, janr yoki tavsif bo‘yicha qidirish\n• 🗂 Janrlar — janr tanlash\n• ⭐ Sevimlilar — saqlangan filmlar\n• 🕘 Ko‘rilganlar — ko‘rilgan filmlar tarixi\n\nTomosha havolalari va yuklangan videolar faqat ruxsat etilgan kontent uchun ishlatilishi kerak.",
        "admin_only": "Bu buyruq faqat bot administratorlari uchun.",
        "admin_saved": "✅ Film katalogga qo‘shildi. ID: {id}", "admin_cancelled": "Film qo‘shish bekor qilindi.",
        "admin_start": "Yangi film qo‘shish boshlandi. Bekor qilish: /cancel\n\n1/10. Film nomini o‘zbek tilida yuboring:",
        "admin_title_ru": "2/10. Film nomini rus tilida yuboring:", "admin_year": "3/10. Chiqqan yilini kiriting (masalan, 2024):",
        "admin_genre_uz": "4/10. Janrni o‘zbek tilida kiriting (masalan, Drama):",
        "admin_genre_ru": "5/10. Janrni rus tilida kiriting (masalan, Драма):",
        "admin_rating": "6/10. Reytingni 0–10 oralig‘ida kiriting yoki o‘tkazib yuborish uchun - yuboring:",
        "admin_duration": "7/10. Davomiyligini daqiqalarda kiriting yoki - yuboring:",
        "admin_desc_uz": "8/10. Film tavsifini o‘zbek tilida yuboring:",
        "admin_desc_ru": "9/10. Film tavsifini rus tilida yuboring:",
        "admin_poster": "10/10. Poster rasmini yuboring (photo), postersiz saqlash uchun - yuboring:",
        "admin_watch": "Tomosha uchun HTTPS havolani yuboring. Botga video yuklash uchun VIDEO deb yozing, havolasiz saqlash uchun - yuboring.",
        "admin_video": "Endi ruxsat etilgan videoni yuboring (Telegram video). O‘tkazib yuborish uchun - yuboring.",
        "admin_bad_year": "Yilni 1880–2100 oralig‘idagi son sifatida kiriting.",
        "admin_bad_rating": "Reyting 0 dan 10 gacha bo‘lishi yoki - bo‘lishi kerak.",
        "admin_bad_duration": "Davomiylik musbat son yoki - bo‘lishi kerak.",
        "admin_bad_url": "Havola HTTPS bilan boshlanishi va to‘g‘ri URL bo‘lishi kerak. Yoki VIDEO / - yuboring.",
        "admin_need_photo": "Iltimos, poster rasmini photo sifatida yuboring yoki - deb yozing.",
        "admin_need_video": "Iltimos, videoni yuboring yoki - deb yozing.",
        "deleted": "✅ Film o‘chirildi.", "delete_missing": "Film topilmadi. ID ni tekshiring.",
        "delete_usage": "Foydalanish: /deletefilm 12", "stats": "📊 Statistika\nFilmlar: {films}\nFoydalanuvchilar: {users}\nSevimlilar: {favorites}\nKo‘rilganlar yozuvi: {watched}",
        "my_id": "Telegram ID: {id}", "search_results": "🔎 Qidiruv natijalari: {count} ta.",
        "unknown": "Kerakli bo‘limni pastdagi menyudan tanlang.", "video_unavailable": "Bu film uchun bot ichida video yuklanmagan.",
    },
    "ru": {
        "welcome": "🎬 Добро пожаловать в мир кино!\n\nВыбирайте фильм в каталоге, ищите по названию, просматривайте жанры и сохраняйте избранное.",
        "films": "🎬 Фильмы", "search": "🔎 Поиск", "genres": "🗂 Жанры",
        "favorites": "⭐ Избранное", "watched": "🕘 История", "language": "🌐 Язык", "help": "ℹ️ Помощь",
        "choose_language": "Выберите язык:", "language_changed": "✅ Язык изменён на русский.",
        "ask_search": "Отправьте название фильма, актёра, жанр или слово из описания. Для отмены: /cancel_search.",
        "search_cancelled": "Поиск отменён.", "empty": "В этом разделе пока нет фильмов.",
        "catalog": "🎬 Каталог фильмов", "page": "Страница", "of": "из", "all_count": "Всего фильмов",
        "details": "🎞 О фильме", "year": "Год", "genre": "Жанр", "rating": "Рейтинг",
        "duration": "Продолжительность", "minutes": "мин.", "no_rating": "не указан",
        "favorite_add": "⭐ В избранное", "favorite_remove": "💛 Убрать из избранного",
        "watched_add": "✅ Отметить просмотренным", "watched_remove": "↩️ Убрать из истории",
        "watch": "▶️ Смотреть", "play_video": "📺 Смотреть в боте", "no_source": "ℹ️ Источник для просмотра ещё не добавлен.",
        "back": "⬅️ Назад", "home": "🏠 Меню", "saved_fav": "Список избранного обновлён.",
        "saved_watched": "История просмотров обновлена.", "not_found": "Фильм не найден.",
        "no_genres": "Жанров пока нет.", "select_genre": "Выберите жанр:",
        "help_text": "Как пользоваться ботом:\n• 🎬 Фильмы — открыть каталог\n• 🔎 Поиск — поиск по названию, жанру или описанию\n• 🗂 Жанры — выбрать жанр\n• ⭐ Избранное — сохранённые фильмы\n• 🕘 История — история просмотров\n\nСсылки для просмотра и загруженные видео должны использоваться только для контента, на который у вас есть права.",
        "admin_only": "Эта команда доступна только администраторам бота.",
        "admin_saved": "✅ Фильм добавлен в каталог. ID: {id}", "admin_cancelled": "Добавление фильма отменено.",
        "admin_start": "Добавление фильма. Отмена: /cancel\n\n1/10. Отправьте название фильма на узбекском:",
        "admin_title_ru": "2/10. Отправьте название фильма на русском:", "admin_year": "3/10. Укажите год выхода (например, 2024):",
        "admin_genre_uz": "4/10. Укажите жанр на узбекском (например, Drama):",
        "admin_genre_ru": "5/10. Укажите жанр на русском (например, Драма):",
        "admin_rating": "6/10. Укажите рейтинг от 0 до 10 или отправьте - чтобы пропустить:",
        "admin_duration": "7/10. Укажите длительность в минутах или - чтобы пропустить:",
        "admin_desc_uz": "8/10. Отправьте описание фильма на узбекском:",
        "admin_desc_ru": "9/10. Отправьте описание фильма на русском:",
        "admin_poster": "10/10. Отправьте постер как фото или отправьте - чтобы сохранить без постера:",
        "admin_watch": "Отправьте HTTPS-ссылку для просмотра. Чтобы загрузить видео в бота, напишите VIDEO; чтобы сохранить без ссылки — отправьте -.",
        "admin_video": "Теперь отправьте разрешённое к публикации видео (Telegram video). Чтобы пропустить, отправьте -.",
        "admin_bad_year": "Укажите год числом от 1880 до 2100.",
        "admin_bad_rating": "Рейтинг должен быть от 0 до 10 или -.",
        "admin_bad_duration": "Длительность должна быть положительным числом или -.",
        "admin_bad_url": "Ссылка должна быть корректным HTTPS URL. Или отправьте VIDEO / -.",
        "admin_need_photo": "Отправьте постер как фото или напишите -.",
        "admin_need_video": "Отправьте видео или напишите -.",
        "deleted": "✅ Фильм удалён.", "delete_missing": "Фильм не найден. Проверьте ID.",
        "delete_usage": "Использование: /deletefilm 12", "stats": "📊 Статистика\nФильмов: {films}\nПользователей: {users}\nИзбранное: {favorites}\nЗаписей о просмотрах: {watched}",
        "my_id": "Telegram ID: {id}", "search_results": "🔎 Найдено фильмов: {count}.",
        "unknown": "Выберите нужный раздел в меню ниже.", "video_unavailable": "Для этого фильма видео в боте не загружено.",
    },
}

MENU_KEYS = ("films", "search", "genres", "favorites", "watched", "language", "help")

# Admin add-film conversation states.
(TITLE_UZ, TITLE_RU, YEAR, GENRE_UZ, GENRE_RU, RATING, DURATION,
 DESC_UZ, DESC_RU, POSTER, WATCH_SOURCE, VIDEO) = range(12)


def tr(language: str, key: str, **kwargs) -> str:
    language = language if language in TEXTS else "uz"
    return TEXTS[language][key].format(**kwargs)


def main_keyboard(language: str) -> ReplyKeyboardMarkup:
    t = TEXTS[language]
    return ReplyKeyboardMarkup(
        [[t["films"], t["search"]], [t["genres"], t["favorites"]],
         [t["watched"], t["language"]], [t["help"]]],
        resize_keyboard=True,
        input_field_placeholder="Film tanlang / Выберите фильм",
    )


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def film_title(film: db.Film, language: str) -> str:
    return film.title_ru if language == "ru" else film.title_uz


def film_genre(film: db.Film, language: str) -> str:
    return film.genre_ru if language == "ru" else film.genre_uz


async def post_init(application: Application) -> None:
    db.init_db()
    commands = [
        BotCommand("start", "Botni ishga tushirish / Запустить бота"),
        BotCommand("help", "Yordam / Помощь"),
        BotCommand("myid", "Telegram ID ni ko‘rish"),
        BotCommand("addfilm", "Film qo‘shish (admin)"),
        BotCommand("deletefilm", "Filmni o‘chirish (admin)"),
        BotCommand("stats", "Statistika (admin)"),
        BotCommand("cancel", "Amalni bekor qilish"),
        BotCommand("cancel_search", "Qidiruvni bekor qilish"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Database initialized; bot is ready.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.effective_message:
        return
    db.upsert_user(user.id, user.username)
    language = db.get_language(user.id)
    context.user_data.pop("awaiting_search", None)
    await update.effective_message.reply_text(tr(language, "welcome"), reply_markup=main_keyboard(language))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return
    lang = db.get_language(update.effective_user.id)
    await update.effective_message.reply_text(tr(lang, "help_text"), reply_markup=main_keyboard(lang))


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user and update.effective_message:
        lang = db.get_language(update.effective_user.id)
        await update.effective_message.reply_text(tr(lang, "my_id", id=update.effective_user.id))


async def cancel_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return
    lang = db.get_language(update.effective_user.id)
    context.user_data.pop("awaiting_search", None)
    context.user_data.pop("last_search", None)
    await update.effective_message.reply_text(tr(lang, "search_cancelled"), reply_markup=main_keyboard(lang))


async def show_language_menu(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = db.get_language(user_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O‘zbekcha", callback_data="lang|uz"),
         InlineKeyboardButton("🇷🇺 Русский", callback_data="lang|ru")],
        [InlineKeyboardButton(tr(lang, "home"), callback_data="home")],
    ])
    await context.bot.send_message(chat_id=chat_id, text=tr(lang, "choose_language"), reply_markup=keyboard)


async def show_genres(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = db.get_language(user_id)
    genres = db.list_genres()
    if not genres:
        await context.bot.send_message(chat_id, tr(lang, "no_genres"), reply_markup=main_keyboard(lang))
        return
    rows = []
    for genre_uz, genre_ru in genres:
        label = genre_ru if lang == "ru" else genre_uz
        key = db.genre_key(genre_uz, genre_ru)
        rows.append([InlineKeyboardButton(label[:60], callback_data=f"list|genre:{key}|0")])
    rows.append([InlineKeyboardButton(tr(lang, "home"), callback_data="home")])
    await context.bot.send_message(chat_id, tr(lang, "select_genre"), reply_markup=InlineKeyboardMarkup(rows))


async def show_film_list(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE,
                         mode: str = "all", page: int = 0, announce: bool = False) -> None:
    lang = db.get_language(user_id)
    query = context.user_data.get("last_search", "") if mode == "search" else ""
    films = db.search_films(query, user_id, mode="all" if mode == "search" else mode)
    total = len(films)
    if total == 0:
        await context.bot.send_message(chat_id, tr(lang, "empty"), reply_markup=main_keyboard(lang))
        return
    max_page = max(0, (total - 1) // PAGE_SIZE)
    page = max(0, min(page, max_page))
    start_at = page * PAGE_SIZE
    selected = films[start_at:start_at + PAGE_SIZE]
    buttons = []
    for film in selected:
        title = film_title(film, lang)
        label = f"{title} ({film.year})"
        buttons.append([InlineKeyboardButton(label[:60], callback_data=f"film|{film.id}|{mode}|{page}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"list|{mode}|{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{max_page + 1}", callback_data="noop"))
    if page < max_page:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"list|{mode}|{page + 1}"))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton(tr(lang, "home"), callback_data="home")])
    text = f"{tr(lang, 'catalog')}\n{tr(lang, 'all_count')}: {total}\n{tr(lang, 'page')} {page + 1} {tr(lang, 'of')} {max_page + 1}"
    if announce and mode == "search":
        text = tr(lang, "search_results", count=total) + "\n" + text
    await context.bot.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))


async def show_film_detail(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE,
                           film_id: int, mode: str = "all", page: int = 0) -> None:
    lang = db.get_language(user_id)
    film = db.get_film(film_id)
    if not film:
        await context.bot.send_message(chat_id, tr(lang, "not_found"), reply_markup=main_keyboard(lang))
        return
    title = film_title(film, lang)
    description = film.description_ru if lang == "ru" else film.description_uz
    rating = film.rating if film.rating else tr(lang, "no_rating")
    duration = f"{film.duration_minutes} {tr(lang, 'minutes')}" if film.duration_minutes else tr(lang, "no_rating")
    caption = (f"{tr(lang, 'details')}: {title}\n\n"
               f"{tr(lang, 'year')}: {film.year}\n"
               f"{tr(lang, 'genre')}: {film_genre(film, lang)}\n"
               f"{tr(lang, 'rating')}: {rating}\n"
               f"{tr(lang, 'duration')}: {duration}\n\n{description}")
    # Telegram photo captions have a 1024 character limit.
    caption = caption[:1000]
    favorite = db.is_favorite(user_id, film_id)
    watched = db.is_watched(user_id, film_id)
    action_row = [InlineKeyboardButton(tr(lang, "favorite_remove" if favorite else "favorite_add"),
                                       callback_data=f"fav|{film_id}|{mode}|{page}")]
    watched_row = [InlineKeyboardButton(tr(lang, "watched_remove" if watched else "watched_add"),
                                        callback_data=f"seen|{film_id}|{mode}|{page}")]
    keyboard_rows = [action_row, watched_row]
    if film.watch_url:
        keyboard_rows.append([InlineKeyboardButton(tr(lang, "watch"), url=film.watch_url)])
    elif film.video_file_id:
        keyboard_rows.append([InlineKeyboardButton(tr(lang, "play_video"), callback_data=f"play|{film_id}")])
    keyboard_rows.append([InlineKeyboardButton(tr(lang, "back"), callback_data=f"list|{mode}|{page}")])
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    if film.poster_file_id:
        await context.bot.send_photo(chat_id, photo=film.poster_file_id, caption=caption, reply_markup=keyboard)
    else:
        await context.bot.send_message(chat_id, caption, reply_markup=keyboard)
    if not film.watch_url and not film.video_file_id:
        await context.bot.send_message(chat_id, tr(lang, "no_source"))


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user or not message.text:
        return
    db.upsert_user(user.id, user.username)
    lang = db.get_language(user.id)
    text = message.text.strip()
    mapping = {TEXTS[lang][key]: key for key in MENU_KEYS}

    if text in mapping:
        context.user_data.pop("awaiting_search", None)
        action = mapping[text]
        if action == "films":
            await show_film_list(message.chat_id, user.id, context, "all", 0)
        elif action == "search":
            context.user_data["awaiting_search"] = True
            await message.reply_text(tr(lang, "ask_search"), reply_markup=main_keyboard(lang))
        elif action == "genres":
            await show_genres(message.chat_id, user.id, context)
        elif action == "favorites":
            await show_film_list(message.chat_id, user.id, context, "favorites", 0)
        elif action == "watched":
            await show_film_list(message.chat_id, user.id, context, "watched", 0)
        elif action == "language":
            await show_language_menu(message.chat_id, user.id, context)
        elif action == "help":
            await message.reply_text(tr(lang, "help_text"), reply_markup=main_keyboard(lang))
        return

    if context.user_data.get("awaiting_search"):
        context.user_data["awaiting_search"] = False
        context.user_data["last_search"] = text[:120]
        await show_film_list(message.chat_id, user.id, context, "search", 0, announce=True)
        return

    await message.reply_text(tr(lang, "unknown"), reply_markup=main_keyboard(lang))


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if not query or not user:
        return
    await query.answer()
    chat_id = query.message.chat_id if query.message else user.id
    data = (query.data or "").split("|")
    action = data[0]
    lang = db.get_language(user.id)

    if action == "noop":
        return
    if action == "home":
        await context.bot.send_message(chat_id, tr(lang, "welcome"), reply_markup=main_keyboard(lang))
        return
    if action == "lang" and len(data) == 2:
        context.user_data.pop("awaiting_search", None)
        db.set_language(user.id, data[1])
        lang = db.get_language(user.id)
        await context.bot.send_message(chat_id, tr(lang, "language_changed"), reply_markup=main_keyboard(lang))
        return
    if action == "list" and len(data) == 3:
        try:
            await show_film_list(chat_id, user.id, context, data[1], int(data[2]))
        except ValueError:
            logger.warning("Invalid list callback: %s", query.data)
        return
    if action == "film" and len(data) == 4:
        try:
            await show_film_detail(chat_id, user.id, context, int(data[1]), data[2], int(data[3]))
        except ValueError:
            logger.warning("Invalid film callback: %s", query.data)
        return
    if action in {"fav", "seen"} and len(data) == 4:
        try:
            film_id, mode, page = int(data[1]), data[2], int(data[3])
            if action == "fav":
                db.toggle_favorite(user.id, film_id)
                await context.bot.send_message(chat_id, tr(lang, "saved_fav"))
            else:
                db.toggle_watched(user.id, film_id)
                await context.bot.send_message(chat_id, tr(lang, "saved_watched"))
            await show_film_detail(chat_id, user.id, context, film_id, mode, page)
        except ValueError:
            logger.warning("Invalid toggle callback: %s", query.data)
        return
    if action == "play" and len(data) == 2:
        try:
            film = db.get_film(int(data[1]))
            if film and film.video_file_id:
                await context.bot.send_video(chat_id, video=film.video_file_id,
                                             caption=film_title(film, lang)[:900])
            else:
                await context.bot.send_message(chat_id, tr(lang, "video_unavailable"))
        except ValueError:
            await context.bot.send_message(chat_id, tr(lang, "not_found"))


async def add_film_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return ConversationHandler.END
    lang = db.get_language(user.id)
    if not is_admin(user.id):
        await message.reply_text(tr(lang, "admin_only"))
        return ConversationHandler.END
    if message.chat.type != ChatType.PRIVATE:
        await message.reply_text("Film qo‘shishni bot bilan shaxsiy chatda bajaring. / Добавляйте фильм в личном чате с ботом.")
        return ConversationHandler.END
    context.user_data["film_draft"] = {}
    await message.reply_text(tr(lang, "admin_start"))
    return TITLE_UZ


async def add_title_uz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    value = update.effective_message.text.strip()
    if not value or len(value) > 200:
        await update.effective_message.reply_text("Nom 1–200 belgidan iborat bo‘lsin.")
        return TITLE_UZ
    context.user_data["film_draft"]["title_uz"] = value
    await update.effective_message.reply_text(tr(lang, "admin_title_ru"))
    return TITLE_RU


async def add_title_ru(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    value = update.effective_message.text.strip()
    if not value or len(value) > 200:
        await update.effective_message.reply_text("Название должно содержать 1–200 символов.")
        return TITLE_RU
    context.user_data["film_draft"]["title_ru"] = value
    await update.effective_message.reply_text(tr(lang, "admin_year"))
    return YEAR


async def add_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    value = update.effective_message.text.strip()
    if not value.isdigit() or not 1880 <= int(value) <= 2100:
        await update.effective_message.reply_text(tr(lang, "admin_bad_year"))
        return YEAR
    context.user_data["film_draft"]["year"] = int(value)
    await update.effective_message.reply_text(tr(lang, "admin_genre_uz"))
    return GENRE_UZ


async def add_genre_uz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    context.user_data["film_draft"]["genre_uz"] = update.effective_message.text.strip()[:100]
    await update.effective_message.reply_text(tr(lang, "admin_genre_ru"))
    return GENRE_RU


async def add_genre_ru(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    context.user_data["film_draft"]["genre_ru"] = update.effective_message.text.strip()[:100]
    await update.effective_message.reply_text(tr(lang, "admin_rating"))
    return RATING


async def add_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    value = update.effective_message.text.strip()
    if value == "-":
        context.user_data["film_draft"]["rating"] = None
    else:
        try:
            number = float(value.replace(",", "."))
            if not 0 <= number <= 10:
                raise ValueError
            context.user_data["film_draft"]["rating"] = f"{number:g}"
        except ValueError:
            await update.effective_message.reply_text(tr(lang, "admin_bad_rating"))
            return RATING
    await update.effective_message.reply_text(tr(lang, "admin_duration"))
    return DURATION


async def add_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    value = update.effective_message.text.strip()
    if value == "-":
        context.user_data["film_draft"]["duration_minutes"] = None
    elif value.isdigit() and 1 <= int(value) <= 1000:
        context.user_data["film_draft"]["duration_minutes"] = int(value)
    else:
        await update.effective_message.reply_text(tr(lang, "admin_bad_duration"))
        return DURATION
    await update.effective_message.reply_text(tr(lang, "admin_desc_uz"))
    return DESC_UZ


async def add_desc_uz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    context.user_data["film_draft"]["description_uz"] = update.effective_message.text.strip()[:4000]
    await update.effective_message.reply_text(tr(lang, "admin_desc_ru"))
    return DESC_RU


async def add_desc_ru(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    context.user_data["film_draft"]["description_ru"] = update.effective_message.text.strip()[:4000]
    await update.effective_message.reply_text(tr(lang, "admin_poster"))
    return POSTER


async def add_poster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    message = update.effective_message
    if message.photo:
        context.user_data["film_draft"]["poster_file_id"] = message.photo[-1].file_id
    elif message.text and message.text.strip() == "-":
        context.user_data["film_draft"]["poster_file_id"] = None
    else:
        await message.reply_text(tr(lang, "admin_need_photo"))
        return POSTER
    await message.reply_text(tr(lang, "admin_watch"))
    return WATCH_SOURCE


def valid_https_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc) and " " not in value
    except Exception:
        return False


async def finish_add_film(update: Update, context: ContextTypes.DEFAULT_TYPE, watch_url: str | None,
                          video_file_id: str | None = None) -> int:
    lang = db.get_language(update.effective_user.id)
    draft = context.user_data.pop("film_draft", {})
    draft["watch_url"] = watch_url
    draft["video_file_id"] = video_file_id
    try:
        film_id = db.add_film(draft)
    except Exception:
        logger.exception("Could not save film to database")
        await update.effective_message.reply_text("❌ Bazaga saqlashda xatolik yuz berdi. DATABASE_URL sozlamasini tekshiring.")
        return ConversationHandler.END
    await update.effective_message.reply_text(tr(lang, "admin_saved", id=film_id))
    return ConversationHandler.END


async def add_watch_source(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    value = update.effective_message.text.strip()
    if value.upper() == "VIDEO":
        await update.effective_message.reply_text(tr(lang, "admin_video"))
        return VIDEO
    if value == "-":
        return await finish_add_film(update, context, None)
    if not valid_https_url(value):
        await update.effective_message.reply_text(tr(lang, "admin_bad_url"))
        return WATCH_SOURCE
    return await finish_add_film(update, context, value)


async def add_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = db.get_language(update.effective_user.id)
    message = update.effective_message
    if message.video:
        return await finish_add_film(update, context, None, message.video.file_id)
    if message.text and message.text.strip() == "-":
        return await finish_add_film(update, context, None)
    await message.reply_text(tr(lang, "admin_need_video"))
    return VIDEO


async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    lang = db.get_language(user.id) if user else "uz"
    context.user_data.pop("film_draft", None)
    if update.effective_message:
        await update.effective_message.reply_text(tr(lang, "admin_cancelled"), reply_markup=main_keyboard(lang))
    return ConversationHandler.END


async def delete_film_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = update.effective_user, update.effective_message
    if not user or not message:
        return
    lang = db.get_language(user.id)
    if not is_admin(user.id):
        await message.reply_text(tr(lang, "admin_only"))
        return
    if not context.args or not context.args[0].isdigit():
        await message.reply_text(tr(lang, "delete_usage"))
        return
    deleted = db.delete_film(int(context.args[0]))
    await message.reply_text(tr(lang, "deleted" if deleted else "delete_missing"))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user, message = update.effective_user, update.effective_message
    if not user or not message:
        return
    lang = db.get_language(user.id)
    if not is_admin(user.id):
        await message.reply_text(tr(lang, "admin_only"))
        return
    await message.reply_text(tr(lang, "stats", **db.get_stats()))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled bot error: %s", context.error, exc_info=context.error)


def build_application() -> Application:
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    add_film_conversation = ConversationHandler(
        entry_points=[CommandHandler("addfilm", add_film_start)],
        states={
            TITLE_UZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title_uz)],
            TITLE_RU: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title_ru)],
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_year)],
            GENRE_UZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_genre_uz)],
            GENRE_RU: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_genre_ru)],
            RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rating)],
            DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_duration)],
            DESC_UZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc_uz)],
            DESC_RU: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_desc_ru)],
            POSTER: [MessageHandler((filters.PHOTO | filters.TEXT) & ~filters.COMMAND, add_poster)],
            WATCH_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_watch_source)],
            VIDEO: [MessageHandler((filters.VIDEO | filters.TEXT) & ~filters.COMMAND, add_video)],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action)],
        allow_reentry=True,
    )
    application.add_handler(add_film_conversation)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myid", my_id))
    application.add_handler(CommandHandler("cancel_search", cancel_search))
    application.add_handler(CommandHandler("deletefilm", delete_film_command))
    application.add_handler(CommandHandler("stats", stats_command))
    # A standalone /cancel also works when no conversation is active.
    application.add_handler(CommandHandler("cancel", cancel_admin_action))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi. .env faylini yoki Render Environment Variables ni sozlang.")
    app = build_application()
    # Render provides RENDER_EXTERNAL_URL. Locally we use long polling for easier testing.
    public_url = (os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")
    if public_url:
        path = os.getenv("WEBHOOK_PATH", secrets.token_urlsafe(24)).strip("/")
        secret = os.getenv("WEBHOOK_SECRET", secrets.token_urlsafe(32))
        logger.info("Starting Telegram webhook server on port %s", os.getenv("PORT", "10000"))
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", "10000")),
            url_path=path,
            webhook_url=f"{public_url}/{path}",
            secret_token=secret,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=False,
        )
    else:
        logger.info("Starting bot with polling (local mode).")
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    main()
