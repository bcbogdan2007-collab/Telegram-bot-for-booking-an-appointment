import asyncio
import logging
import os
import sqlite3
from datetime import date, datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============ НАСТРОЙКИ ============
BOT_TOKEN = os.getenv("telegram_bot_token_here")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # Telegram ID администратора (необязательно)

SHOP_NAME = "BarberKing"
ADDRESS = "г. Москва, ул. Примерная, 10"
PHONE = "+7 (999) 123-45-67"
WORK_HOURS = "Ежедневно, 10:00–20:00"

# id: (название, цена в ₽, длительность в мин)
SERVICES = {
    "1": ("Мужская стрижка", 1500, 60),
    "2": ("Стрижка машинкой", 1000, 30),
    "3": ("Моделирование бороды", 1000, 45),
    "4": ("Стрижка + борода", 2300, 90),
    "5": ("Бритьё опасной бритвой", 1200, 40),
    "6": ("Детская стрижка", 1000, 40),
}

# id: (имя, специализация)
MASTERS = {
    "1": ("Алексей", "Барбер-стилист"),
    "2": ("Дмитрий", "Топ-барбер"),
    "3": ("Максим", "Мастер по бородам"),
}

TIME_SLOTS = ["10:00", "11:00", "12:00", "13:00", "14:00",
              "15:00", "16:00", "17:00", "18:00", "19:00"]
DAYS_AHEAD = 7
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
# ===================================

router = Router()

# ---------- База данных (SQLite) ----------
db = sqlite3.connect("barbershop.db")
db.execute(
    """CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_name TEXT,
        service_id TEXT NOT NULL,
        master_id TEXT NOT NULL,
        day TEXT NOT NULL,
        time TEXT NOT NULL,
        UNIQUE (master_id, day, time)
    )"""
)
db.commit()


def busy_times(master_id: str, day: str) -> set[str]:
    rows = db.execute(
        "SELECT time FROM bookings WHERE master_id=? AND day=?", (master_id, day)
    ).fetchall()
    return {r[0] for r in rows}


def free_times(master_id: str, day: str) -> list[str]:
    busy = busy_times(master_id, day)
    result = []
    for t in TIME_SLOTS:
        if t in busy:
            continue
        # для сегодняшнего дня скрываем время, которое уже прошло
        if day == date.today().isoformat():
            if datetime.strptime(f"{day} {t}", "%Y-%m-%d %H:%M") <= datetime.now():
                continue
        result.append(t)
    return result


def fmt_day(day: str) -> str:
    d = date.fromisoformat(day)
    return f"{d.strftime('%d.%m')} ({WEEKDAYS[d.weekday()]})"


# ---------- Клавиатуры ----------
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="✂️ Записаться", callback_data="book")
    kb.button(text="💈 Услуги и цены", callback_data="services")
    kb.button(text="👨‍🎤 Наши мастера", callback_data="masters")
    kb.button(text="📅 Мои записи", callback_data="my")
    kb.button(text="📍 Контакты", callback_data="contacts")
    kb.adjust(1, 2, 2)
    return kb.as_markup()


def back_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 В главное меню", callback_data="menu")
    return kb.as_markup()


WELCOME = (
    f"💈 <b>Добро пожаловать в {SHOP_NAME}!</b>\n"
    "(для заказа такого бота для любых задач с полным обслуживанием напишите сюда: @dark_baga7)\n\n"
    "Выберите, что вас интересует:"
)


# ---------- Главное меню ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME, reply_markup=main_menu())


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(WELCOME, reply_markup=main_menu())


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    await call.message.edit_text(WELCOME, reply_markup=main_menu())
    await call.answer()


# ---------- Услуги / мастера / контакты ----------
@router.callback_query(F.data == "services")
async def cb_services(call: CallbackQuery):
    lines = [f"• {name} — <b>{price} ₽</b> ({dur} мин)" for name, price, dur in SERVICES.values()]
    kb = InlineKeyboardBuilder()
    kb.button(text="✂️ Записаться", callback_data="book")
    kb.button(text="🏠 В меню", callback_data="menu")
    kb.adjust(1)
    await call.message.edit_text("💈 <b>Услуги и цены:</b>\n\n" + "\n".join(lines), reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "masters")
async def cb_masters(call: CallbackQuery):
    lines = [f"• <b>{name}</b> — {spec}" for name, spec in MASTERS.values()]
    kb = InlineKeyboardBuilder()
    kb.button(text="✂️ Записаться", callback_data="book")
    kb.button(text="🏠 В меню", callback_data="menu")
    kb.adjust(1)
    await call.message.edit_text("👨‍🎤 <b>Наши мастера:</b>\n\n" + "\n".join(lines), reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data == "contacts")
async def cb_contacts(call: CallbackQuery):
    text = f"📍 <b>Контакты</b>\n\nАдрес: {ADDRESS}\nТелефон: {PHONE}\nЧасы работы: {WORK_HOURS}"
    await call.message.edit_text(text, reply_markup=back_menu())
    await call.answer()


# ---------- Запись: шаг 1 — выбор услуги ----------
@router.callback_query(F.data == "book")
async def cb_book(call: CallbackQuery):
    kb = InlineKeyboardBuilder()
    for sid, (name, price, _) in SERVICES.items():
        kb.button(text=f"{name} — {price} ₽", callback_data=f"svc:{sid}")
    kb.button(text="🏠 В меню", callback_data="menu")
    kb.adjust(1)
    await call.message.edit_text("✂️ <b>Шаг 1/4.</b> Выберите услугу:", reply_markup=kb.as_markup())
    await call.answer()


# ---------- Шаг 2 — выбор мастера ----------
@router.callback_query(F.data.startswith("svc:"))
async def cb_service(call: CallbackQuery):
    sid = call.data.split(":")[1]
    kb = InlineKeyboardBuilder()
    for mid, (name, spec) in MASTERS.items():
        kb.button(text=f"{name} · {spec}", callback_data=f"m:{sid}:{mid}")
    kb.button(text="⬅️ Назад", callback_data="book")
    kb.adjust(1)
    await call.message.edit_text(
        f"Услуга: <b>{SERVICES[sid][0]}</b>\n\n<b>Шаг 2/4.</b> Выберите мастера:",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


# ---------- Шаг 3 — выбор даты ----------
@router.callback_query(F.data.startswith("m:"))
async def cb_master(call: CallbackQuery):
    _, sid, mid = call.data.split(":")
    kb = InlineKeyboardBuilder()
    for i in range(DAYS_AHEAD):
        day = (date.today() + timedelta(days=i)).isoformat()
        if free_times(mid, day):
            kb.button(text=fmt_day(day), callback_data=f"d:{sid}:{mid}:{day}")
    kb.button(text="⬅️ Назад", callback_data=f"svc:{sid}")
    kb.adjust(3, 3, 1, 1)
    await call.message.edit_text(
        f"Услуга: <b>{SERVICES[sid][0]}</b>\nМастер: <b>{MASTERS[mid][0]}</b>\n\n"
        f"<b>Шаг 3/4.</b> Выберите дату:",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


# ---------- Шаг 4 — выбор времени ----------
@router.callback_query(F.data.startswith("d:"))
async def cb_day(call: CallbackQuery):
    _, sid, mid, day = call.data.split(":")
    times = free_times(mid, day)
    kb = InlineKeyboardBuilder()
    for t in times:
        kb.button(text=t, callback_data=f"t:{sid}:{mid}:{day}:{t.replace(':', '')}")
    kb.button(text="⬅️ Назад", callback_data=f"m:{sid}:{mid}")
    kb.adjust(3)
    text = (
        f"Услуга: <b>{SERVICES[sid][0]}</b>\nМастер: <b>{MASTERS[mid][0]}</b>\n"
        f"Дата: <b>{fmt_day(day)}</b>\n\n<b>Шаг 4/4.</b> Выберите время:"
    )
    if not times:
        text = "😔 На эту дату свободного времени нет. Выберите другую дату."
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


# ---------- Подтверждение ----------
@router.callback_query(F.data.startswith("t:"))
async def cb_time(call: CallbackQuery):
    _, sid, mid, day, tt = call.data.split(":")
    time = f"{tt[:2]}:{tt[2:]}"
    name, price, dur = SERVICES[sid]
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=f"ok:{sid}:{mid}:{day}:{tt}")
    kb.button(text="⬅️ Изменить время", callback_data=f"d:{sid}:{mid}:{day}")
    kb.button(text="❌ Отмена", callback_data="menu")
    kb.adjust(1)
    await call.message.edit_text(
        "📝 <b>Проверьте запись:</b>\n\n"
        f"Услуга: {name}\nМастер: {MASTERS[mid][0]}\n"
        f"Дата: {fmt_day(day)}\nВремя: {time}\n"
        f"Стоимость: {price} ₽ · {dur} мин",
        reply_markup=kb.as_markup(),
    )
    await call.answer()


@router.callback_query(F.data.startswith("ok:"))
async def cb_confirm(call: CallbackQuery, bot: Bot):
    _, sid, mid, day, tt = call.data.split(":")
    time = f"{tt[:2]}:{tt[2:]}"
    user = call.from_user
    try:
        db.execute(
            "INSERT INTO bookings (user_id, user_name, service_id, master_id, day, time) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user.id, user.full_name, sid, mid, day, time),
        )
        db.commit()
    except sqlite3.IntegrityError:
        kb = InlineKeyboardBuilder()
        kb.button(text="Выбрать другое время", callback_data=f"d:{sid}:{mid}:{day}")
        await call.message.edit_text("😔 Это время только что заняли.", reply_markup=kb.as_markup())
        await call.answer()
        return

    await call.message.edit_text(
        f"✅ <b>Вы записаны!</b>\n\n{SERVICES[sid][0]}\nМастер: {MASTERS[mid][0]}\n"
        f"{fmt_day(day)} в {time}\n\nЖдём вас по адресу: {ADDRESS}",
        reply_markup=back_menu(),
    )
    await call.answer("Запись создана!")

    if ADMIN_ID:
        username = f"@{user.username}" if user.username else user.full_name
        await bot.send_message(
            ADMIN_ID,
            f"🔔 Новая запись\n{username}\n{SERVICES[sid][0]} · {MASTERS[mid][0]}\n{fmt_day(day)} {time}",
        )


# ---------- Мои записи / отмена ----------
@router.callback_query(F.data == "my")
async def cb_my(call: CallbackQuery):
    rows = db.execute(
        "SELECT id, service_id, master_id, day, time FROM bookings "
        "WHERE user_id=? AND day>=? ORDER BY day, time",
        (call.from_user.id, date.today().isoformat()),
    ).fetchall()
    kb = InlineKeyboardBuilder()
    if not rows:
        text = "📅 У вас пока нет активных записей."
        kb.button(text="✂️ Записаться", callback_data="book")
    else:
        lines = []
        for bid, sid, mid, day, time in rows:
            lines.append(f"• {fmt_day(day)} {time} — {SERVICES[sid][0]}, {MASTERS[mid][0]}")
            kb.button(text=f"❌ Отменить {fmt_day(day)} {time}", callback_data=f"cancel:{bid}")
        text = "📅 <b>Ваши записи:</b>\n\n" + "\n".join(lines)
    kb.button(text="🏠 В меню", callback_data="menu")
    kb.adjust(1)
    await call.message.edit_text(text, reply_markup=kb.as_markup())
    await call.answer()


@router.callback_query(F.data.startswith("cancel:"))
async def cb_cancel(call: CallbackQuery):
    bid = int(call.data.split(":")[1])
    db.execute("DELETE FROM bookings WHERE id=? AND user_id=?", (bid, call.from_user.id))
    db.commit()
    await call.answer("Запись отменена")
    await cb_my(call)


# ---------- Запуск ----------
async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
  
