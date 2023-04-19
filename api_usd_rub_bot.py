import os
import datetime
import requests
import sqlite3
import pytz
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
import random

load_dotenv()

DB_NAME = 'users.db'

def create_database():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, special_message TEXT)')

def set_user_name(chat_id: int, special_message: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (chat_id, special_message) VALUES (?, ?)", (chat_id, special_message))
        conn.commit()

def get_random_pet_name(chat_id):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT special_message FROM users WHERE chat_id=?", (chat_id,))
        special_message = cursor.fetchone()

    if special_message and special_message[0]:
        return special_message[0]
    else:
        pet_names = [
            "котик",
            "зайчик",
            "медвежонок",
            "слоненок",
            "леопардик",
            "лисенок",
            "тигренок",
        ]
        return random.choice(pet_names)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

previous_rates = {"usd": None, "eur": None}

create_database()


def get_exchange_rates():
    response = requests.get("https://www.floatrates.com/daily/usd.json")
    data = response.json()
    usd_rate = data["rub"]["rate"]

    response = requests.get("https://www.floatrates.com/daily/eur.json")
    data = response.json()
    eur_rate = data["rub"]["rate"]

    return usd_rate, eur_rate

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    set_user_name(chat_id, None)
    print(f"User chat_id: {chat_id}")
    update.message.reply_text("Привет! Я буду отправлять тебе курс доллара и евро к рублю раз в сутки в 8 часов по МСК!😊\nКоманда:\n/set_name Ваше_Имя - дает возможность выбрать псевдоним")

    send_button(update, context)

def send_exchange_rates(context: CallbackContext):
    global previous_rates
    usd_rate, eur_rate = get_exchange_rates()
    formatted_usd_rate = "{:.1f}".format(usd_rate)
    formatted_eur_rate = "{:.1f}".format(eur_rate)

    usd_message = f"Курс доллара к рублю: {formatted_usd_rate}\n"
    eur_message = f"Курс евро к рублю: {formatted_eur_rate}\n"

    if previous_rates["usd"]:
        usd_diff = usd_rate - previous_rates["usd"]
        if usd_diff > 0:
            usd_message += f" Ого, курс доллара вырос на {usd_diff:.1f} рубля! Что же будет дальше?"
        elif usd_diff < 0:
            usd_message += f" Курс доллара упал на {-usd_diff:.1f} рубля. Держим кулачки, братья!"

    if previous_rates["eur"]:
        eur_diff = eur_rate - previous_rates["eur"]
        if eur_diff > 0:
            eur_message += f"Ого, курс евро вырос на {eur_diff:.1f} рубля! Что же будет дальше?"
        elif eur_diff < 0:
            eur_message += f"Курс евро упал на {-eur_diff:.1f} рубля. Держим кулачки, братья!"

    previous_rates["usd"] = usd_rate
    previous_rates["eur"] = eur_rate

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users")
        chat_ids = cursor.fetchall()

    for chat_id_tuple in chat_ids:
        chat_id = chat_id_tuple[0]
        context.bot.send_message(chat_id=chat_id, text=f"{usd_message}\n{eur_message}")


def get_now(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    usd_rate, eur_rate = get_exchange_rates()
    formatted_usd_rate = "{:.1f}".format(usd_rate)
    formatted_eur_rate = "{:.1f}".format(eur_rate)
    
    random_pet_name = get_random_pet_name(chat_id)
    update.message.reply_text(f"Текущий курс доллара к рублю: {formatted_usd_rate}\nТекущий курс евро к рублю: {formatted_eur_rate}\nДоброго времени суток, {random_pet_name}!")

def set_name(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    special_message = ' '.join(context.args)
    
    if special_message:
        set_user_name(chat_id, special_message)
        update.message.reply_text(f"Теперь я буду называть тебя {special_message}!")
    else:
        update.message.reply_text("Пожалуйста, используйте команду /set_name с вашим именем или псевдонимом после команды через пробел.")

def send_button(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    keyboard = [
        [KeyboardButton("Получить курс сейчас")],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    context.bot.send_message(chat_id=chat_id, text="Нажмите на кнопку, чтобы получить текущий курс:", reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "getnow":
        chat_id = query.message.chat_id
        get_now(update, context)
        send_button(update, context)

def get_first_run_time():
    msk_tz = pytz.timezone("Europe/Moscow")
    now = datetime.datetime.now(msk_tz)
    next_run_time = now.replace(hour=8, minute=0, second=0, microsecond=0)

    if now.time() > next_run_time.time():
        next_run_time += datetime.timedelta(days=1)

    return next_run_time

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("getnow", get_now))
    dp.add_handler(CommandHandler("set_name", set_name, pass_args=True))
    dp.add_handler(MessageHandler(Filters.text("Получить курс сейчас"), get_now))
    dp.add_handler(MessageHandler(Filters.text, start))
    dp.add_handler(CallbackQueryHandler(button_handler))

    job_queue = updater.job_queue
    first_run_time = get_first_run_time()
    job_queue.run_repeating(send_exchange_rates, interval=datetime.timedelta(days=1), first=first_run_time)


    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()