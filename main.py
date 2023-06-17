import logging
import csv

from telegram import Update, ReplyKeyboardMarkup, __version__ as TG_VER
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Define questions and options
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
    """Send a message when the command /start is issued."""
    user = update.effective_user
    keyboard = ReplyKeyboardMarkup([QUESTIONS_OPTIONS[0]], one_time_keyboard=True)
    await update.message.reply_text(
        QUESTIONS_TEXT[0],
        reply_markup=keyboard,
    )
    context.user_data['current_question'] = 0

async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the next question and save the answer to the previous question."""
    user = update.effective_user
    answer = update.message.text
    current_question = context.user_data['current_question']
    save_answer(user, QUESTIONS_TEXT[current_question], answer)
    if current_question < len(QUESTIONS_TEXT) - 1:
        keyboard = ReplyKeyboardMarkup([QUESTIONS_OPTIONS[current_question + 1]], one_time_keyboard=True)
        await update.message.reply_text(QUESTIONS_TEXT[current_question + 1], reply_markup=keyboard)
        context.user_data['current_question'] = current_question + 1
    else:
        await update.message.reply_text("Thank you for completing the survey!")
        return -1


def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("6232551131:AAG2-8nMYPJgB_ihvwRHpALG8NIhAk4NiSw").build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, next_question))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
