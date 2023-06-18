import logging
import csv
import sqlite3
import asyncio
from telegram import Update, ReplyKeyboardMarkup, __version__ as TG_VER
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Database setup
conn = sqlite3.connect('subscribers.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS subscribers (telegram_id text, subscribed text)''')

def save_subscriber(telegram_id):
    c.execute("SELECT telegram_id FROM subscribers WHERE telegram_id = ?", (telegram_id,))
    if c.fetchone() is None:
        c.execute("INSERT INTO subscribers VALUES (?, 'subscribed')", (telegram_id,))
    else:
        c.execute("UPDATE subscribers SET subscribed = 'subscribed' WHERE telegram_id = ?", (telegram_id,))
    conn.commit()



QUESTIONS_TEXT = [
     "Як Ви оцінюєте свою підготовку до виконання практичних завдань в лікарні?",
    "Якими Ви оцінюєте свої знання з організації роботи в лікарнях?",
    "Ваш рівень знань щодо правильного оформлення медичної документації:",
    "Як впевнено Ви проводите опитування пацієнтів та заповнюєте історію хвороби?",
    "Чи відчуваєте Ви нестачу навичок для вирішення конфліктних ситуацій?",
    "Чи знаєте Ви, як шукати стажування та навчальні курси для розвитку в медицині?",
    "Чи маєте Ви досвід волонтерства або роботи в медичних організаціях під час навчання?",
    "Чи знаєте Ви про можливості використання медичних технологій, зокрема електронних медичних записів?",
    "Чи відчуваєте Ви нестачу soft skills для співпраці з лікарями?",
    "Чи маєте Ви досвід участі в наукових дослідженнях та публікаціях?",
    "Чи вважаєте Ви, що медичні університети достатньо підготовлюють студентів з правових аспектів медичної практики?",
    "Чи маєте Ви досвід роботи з психологічними аспектами медичної практики, такими як емоційне виснаження, стрес або співчуття?",
    "Чи вважаєте Ви, що є потреба в створенні додаткових програм або ініціатив для підтримки молодих медичних спеціалістів в Україні?",
    "Чи достатньо, на Вашу думку, аспектів медичної етики розглядається під час навчання у медичних університетах?"
]

QUESTIONS_OPTIONS = [
    ["незадовільними", "достатніми", "хорошими", "відмінними"],
    ["незадовільними", "достатніми", "хорошими", "відмінними"],
    ["незадовільний", "достатній", "хороший", "відмінний"],
    ["невпевнено", "з певними труднощами", "впевнено", "дуже впевнено"],
    ["так", "ні"],
    ["так", "ні"],
    ["так", "ні"],
    ["так", "ні"],
    ["так", "ні"],
    ["так", "ні"],
    ["так", "ні"],
    ["так", "ні"],
    ["так", "ні"],
    ["так", "ні"]
]

# Define CSV file name
CSV_FILE = "survey_results.csv"

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def save_answer(user, question, answer):
    """Save the user's answer to a CSV file."""
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([user, question, answer])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    save_subscriber(user.id)
    logger.info(f"User {user.id} started the bot")
    keyboard = ReplyKeyboardMarkup([QUESTIONS_OPTIONS[0]], one_time_keyboard=True)
    await update.message.reply_text(
        QUESTIONS_TEXT[0],
        reply_markup=keyboard,
    )
    context.user_data['current_question'] = 0


async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    answer = update.message.text
    current_question = context.user_data['current_question']
    save_answer(user, QUESTIONS_TEXT[current_question], answer)
    logger.info(f"User {user.id} answered question {current_question} with {answer}")
    if current_question < len(QUESTIONS_TEXT) - 1:
        keyboard = ReplyKeyboardMarkup([QUESTIONS_OPTIONS[current_question + 1]], one_time_keyboard=True)
        await update.message.reply_text(QUESTIONS_TEXT[current_question + 1], reply_markup=keyboard)
        context.user_data['current_question'] = current_question + 1
    else:
        await update.message.reply_text("Thank you for completing the survey!")
        return -1

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != 358654127:
        return
    message = ' '.join(context.args)
    for row in c.execute('SELECT telegram_id FROM subscribers'):
        try:
            await context.bot.send_message(chat_id=row[0], text=message)
            logger.info(f"Sent message to subscriber {row[0]}")
            await asyncio.sleep(1)  # wait for 1 second
        except Exception as e:
            logger.error(f"Failed to send message to subscriber {row[0]}: {e}")
            c.execute("UPDATE subscribers SET subscribed = 'unsubscribed' WHERE telegram_id = ?", (row[0],))
            conn.commit()


def main() -> None:
    application = Application.builder().token("6232551131:AAG2-8nMYPJgB_ihvwRHpALG8NIhAk4NiSw").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, next_question))
    application.run_polling()

if __name__ == '__main__':
    main()
