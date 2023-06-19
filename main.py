import logging
import csv
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Contact
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from datetime import datetime
user_scores = {}
# Database setup
conn = sqlite3.connect('subscribers.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS subscribers 
             (telegram_id text, subscribed text)''')
c.execute("PRAGMA table_info(subscribers)")
columns = [column[1] for column in c.fetchall()]
if 'subscribed' not in columns:
    c.execute("ALTER TABLE subscribers ADD COLUMN subscribed text DEFAULT 'subscribed'")


def save_subscriber(telegram_id, phone_number, email):
    c.execute("SELECT telegram_id FROM subscribers WHERE telegram_id = ?", (telegram_id,))
    if c.fetchone() is None:
        c.execute("INSERT INTO subscribers VALUES (?, ?, ?, 'subscribed')", (telegram_id, phone_number, email))
    else:
        c.execute("UPDATE subscribers SET phone_number = ?, email = ?, subscribed = 'subscribed' WHERE telegram_id = ?", (phone_number, email, telegram_id))
    conn.commit()




QUESTION_TEXT = [
    "1. Чи маєте ви досвід в лікарні? (асистенція, медсестринство, стажування)",
    "2. Чи проводили ви опитування та огляд пацієнтів?",
    "3. Чи вмієте ви швидко та якісно заповнювати медичну документацію? (історія хвороби, виписка, щоденник, протокол операції і т.д)",
    "4. Чи вмієте ви знаходити компроміс в конфліктних ситуаціях?",
    "5. Чи знаєте ви, як і де шукати стажування та навчальні курси для розвитку в медицині?",
    "6. Чи знаєте ви як користуватися медичними інформаційними системами (МІС), зокрема, як вести електронні медичні записи?",
    "7. Чи знаєте ви як співпрацювати з наставником так щоб він був зацікавлений вас навчити?",
    "8. Чи маєте Ви досвід участі в наукових дослідженнях та публікаціях?",
    "9. Чи знаєте ви законодавчу базу необхідну для практичної діяльності лікаря (зокрема, з метою юридичного захисту)?",
    "10.Чи потрібні вам додаткові програми для розвитку себе як конкурентноспроможного і затребуваного спеціаліста в медичній сфері в Україні?"
]

QUESTION_OPTIONS = [
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
CSV_FILE = 'results.csv'  # Specify the name of your CSV file here

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def save_answer(user, question, answer_index, context):
    """Save the user's answer to a CSV file."""
    # Convert the answer index to an integer
    answer_index = int(answer_index)
    # Get the current question index
    current_question = QUESTION_TEXT.index(question)
    # Get the answer text from QUESTION_OPTIONS
    answer_text = QUESTION_OPTIONS[current_question][answer_index]
    context.user_data['answers'].append(answer_text)
    user_id = user.id
    if user_id not in user_scores:
        user_scores[user_id] = []
    user_scores[user_id].append(answer_index)
def calculate_score(user_id):
    answers = user_scores[user_id]
    total_questions = 10
    score = 100
    for answer in answers:
        if answer.lower() == 'ні':
            score -= 10
    return score
async def request_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Share Contact", request_contact=True)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please share your contact information.", reply_markup=reply_markup)
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact = update.message.contact
    # Save the phone number to the user data
    context.user_data['phone_number'] = contact.phone_number
    # Request the user's email
    await request_email(update, context)

async def request_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Please enter your email.")
async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    email = update.message.text
    user_id = update.effective_user.id
    # Save the email to the user data
    context.user_data['email'] = email
    # Start the quiz
    await start(update, context)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Initialize the answers for the user
    context.user_data['answers'] = []

    # Get the user
    user = update.effective_user

    # Retrieve the phone number and email from the user data
    phone_number = context.user_data.get('phone_number')
    email = context.user_data.get('email')

    # Save the subscriber's information
    save_subscriber(user.id, phone_number, email)

    logger.info(f"User {user.id} started the bot")

    # Create the keyboard for the first question
    keyboard = [
        [InlineKeyboardButton(option, callback_data=str(index)) for index, option in enumerate(QUESTION_OPTIONS[0])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the first question
    await update.message.reply_text(
        QUESTION_TEXT[0],
        reply_markup=reply_markup,
    )

    # Set the current question to 0
    context.user_data['current_question'] = 0

    # Clear the answers for the user
    user_scores[user.id] = []


async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    user_id = user.id
    answer = query.data
    current_question = context.user_data['current_question']
    save_answer(user, QUESTION_TEXT[current_question], answer, context)
    logger.info(f"User {user.id} answered question {current_question} with {answer}")
    if current_question < len(QUESTION_TEXT) - 1:
        keyboard = [
            [
                InlineKeyboardButton(option, callback_data=str(index))
                for index, option in enumerate(QUESTION_OPTIONS[current_question + 1][:2])
                # First two options in the current_question list
            ],
            [
                InlineKeyboardButton(option, callback_data=str(index))
                for index, option in enumerate(QUESTION_OPTIONS[current_question + 1][2:])
                # Last two options in the current_question list
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=QUESTION_TEXT[current_question + 1],
            reply_markup=reply_markup,
        )
        context.user_data['current_question'] = current_question + 1
    else:
        score = await calculate_score(context.user_data['answers'])
        await save_final_result(user, context.user_data['answers'], score, context)

        # Determine the status based on the score
        if 90 <= score <= 100:
               status = "Крутий інтерн 😎"
        elif 70 <= score < 90:
                status = "Перспективний інтерн 😏"
        elif 50 <= score < 70:
                status = "Компетентний інтерн 🧐"
        else:
                status = "Інтерн початківець 👶"

        await query.edit_message_text(
                text=f"""Результати: Рівень вашої готовності *{score}%*
Ваш статус: {status}"""
        )
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

async def calculate_score(answers):
    total_questions = 10
    score = 100
    for answer in answers:
        if answer == 'ні':  # 'ні' is considered as 'no'
            score -= 10
    return score
async def save_final_result(user, answers, score, context):
    """Save the user's final result to a CSV file."""
    try:
        with open(CSV_FILE, 'x', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Timestamp', 'User', 'Final Result', 'Answers', 'Score'])
    except FileExistsError:
        pass
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, user, 'Final Result', answers, score])

def main() -> None:
    application = Application.builder().token("6232551131:AAG2-8nMYPJgB_ihvwRHpALG8NIhAk4NiSw").build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email))
    application.add_handler(CallbackQueryHandler(next_question))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start", request_contact))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, next_question))
    application.run_polling()

if __name__ == '__main__':
    main()
