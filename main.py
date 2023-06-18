import logging
import csv
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
answers = []
# Database setup
conn = sqlite3.connect('subscribers.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS subscribers 
             (telegram_id text, subscribed text)''')
c.execute("PRAGMA table_info(subscribers)")
columns = [column[1] for column in c.fetchall()]
if 'subscribed' not in columns:
    c.execute("ALTER TABLE subscribers ADD COLUMN subscribed text DEFAULT 'subscribed'")


def save_subscriber(telegram_id):
    c.execute("SELECT telegram_id FROM subscribers WHERE telegram_id = ?", (telegram_id,))
    if c.fetchone() is None:
        c.execute("INSERT INTO subscribers VALUES (?, 'subscribed')", (telegram_id,))
    else:
        c.execute("UPDATE subscribers SET subscribed = 'subscribed' WHERE telegram_id = ?", (telegram_id,))
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
CSV_FILE = "survey_results.csv"

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
async def calculate_score():
    total_questions = 10
    score = 100
    for answer in answers:
        if answer.lower() == 'ні':
            score -= 10
    return score
def save_answer(user, question, answer_index):
    """Save the user's answer to a CSV file."""
    # Convert the answer index to an integer
    answer_index = int(answer_index)
    # Get the current question index
    current_question = QUESTION_TEXT.index(question)
    # Get the answer text from QUESTION_OPTIONS
    answer_text = QUESTION_OPTIONS[current_question][answer_index]
    answers.append(answer_text)
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([user, question, answer_text])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    save_subscriber(user.id)
    logger.info(f"User {user.id} started the bot")
    keyboard = [
        [
            InlineKeyboardButton(option, callback_data=str(index))
            for index, option in enumerate(QUESTION_OPTIONS[0][:2])  # First two options in the first row
        ],

    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        QUESTION_TEXT[0],
        reply_markup=reply_markup,
    )
    context.user_data['current_question'] = 0


async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    answer = query.data
    current_question = context.user_data['current_question']
    save_answer(user, QUESTION_TEXT[current_question], answer)
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
        score = await calculate_score()
        await query.edit_message_text(text=f"""Результати: Рівень вашої готовності {score}%
            Ваш статус:
            90%-100% : Крутий інтерн 😎
            70-89% : Перспективний інтерн 😏
            50-69% : Компетентний інтерн 🧐
            0 - 49% : Інтерн початківець 👶""")
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
        if answer.lower() == 'ні':
            score -= 10
    return score

def main() -> None:
    application = Application.builder().token("6232551131:AAG2-8nMYPJgB_ihvwRHpALG8NIhAk4NiSw").build()
    application.add_handler(CallbackQueryHandler(next_question))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, next_question))
    application.run_polling()

if __name__ == '__main__':
    main()
