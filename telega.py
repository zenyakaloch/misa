import os
from PIL import Image
import pytesseract
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PyPDF2 import PdfReader
import openai
import config
from database import Database
import tiktoken

openai.api_key = config.AI_TOKEN
db = Database()

instruction_test = "your task: complete the test, if there is an ordinal number or letter before the answer, output only question number and this symbol and the correct answer."
instruction_chat = "In no case do not answer in Russian, if the question is asked in Russian, answer in Ukrainian as a matter of principle"

chat_v_4 = "gpt-4o"
chat_v_4_mini = "gpt-4o-mini"

# Вибір кодувальника для моделі
encoding = tiktoken.encoding_for_model("gpt-4o")


def count_tokens(text, chat_v):

    encoding = tiktoken.encoding_for_model(chat_v)
    # Підрахунок токенів за допомогою tiktoken
    return len(encoding.encode(text))


def send_text_to_chatgpt(text, instruction, chat_v):

    # Підрахунок вхідних токенів
    input_tokens = count_tokens(instruction + "\n\n" + text, chat_v)

    response = openai.ChatCompletion.create(
        model=chat_v,
        messages=[
            {"role": "system", "content": "you are a doctor."},
            {"role": "user", "content": instruction + "\n\n" + text}
        ]
    )

    output_text = response['choices'][0]['message']['content']
    total_tokens = response['usage']['total_tokens']
    output_tokens = total_tokens - input_tokens

    i = int(input_tokens)
    i = i / 4
    o = int(output_tokens)
    count = o + i

    if chat_v == "gpt-4o-mini":
        count = count / 8

    count = round(count)
    print(output_text)

    return output_text, count

def find_question(text):
    lf = text.find("Відповіді ще не було")
    rf = text.rfind("Відповіді ще не було")
    if lf != -1:
        sections = text.split("Відповіді ще не було")
        if lf != rf:
            return sections[1]
        else:
            for section in sections:
                if "Виберіть одну відповідь:" in section:
                    return section
    else:
        return text


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")
        

    if update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        file_path = os.path.join(os.getcwd(), f"{photo.file_unique_id}.jpg")
        await file.download_to_drive(file_path)

        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang='ukr+eng')
            text = find_question(text)

            user_tokens = db.get_user_tokens(user.id)

            if user_tokens > 0:
                response, tokens_used = send_text_to_chatgpt(text, instruction_test, chat_v_4)
                new_balance = user_tokens - tokens_used
                db.update_user_tokens(user.id, new_balance)

                await update.message.reply_text(
                    f"Відповідь: {response}\nВикористано токенів: {tokens_used}\n")
            else:
                await update.message.reply_text(
                    f"Ваш баланс токенів: {user_tokens}. Потрібно поповнити баланс для продовження.")
        except Exception as e:
            await update.message.reply_text(f"Виникла помилка під час обробки зображення: {str(e)}")
        finally:
            os.remove(file_path)
    else:
        await update.message.reply_text("Надішліть зображення.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")

    if update.message.document and update.message.document.mime_type == "application/pdf":
        document = update.message.document
        file = await document.get_file()
        file_path = os.path.join(os.getcwd(), document.file_name)
        await file.download_to_drive(file_path)

        try:
            reader = PdfReader(file_path)
            text = ''
            for page in reader.pages:
                text += page.extract_text() + '\n'
            text = text.replace("Питання", "").replace("Відповіді ще не було", "").strip()

            user_tokens = db.get_user_tokens(user.id)

            if user_tokens > 0:
                response, tokens_used = send_text_to_chatgpt(text, instruction_test, chat_v_4)
                new_balance = user_tokens - tokens_used
                db.update_user_tokens(user.id, new_balance)

                await update.message.reply_text(
                    f"Відповідь: {response}\nВикористано токенів: {tokens_used}")
            else:
                await update.message.reply_text(
                    f"Ваш баланс токенів: {user_tokens}. Потрібно поповнити баланс для продовження.")
        except Exception as e:
            await update.message.reply_text(f"Виникла помилка під час обробки документа: {str(e)}")
        finally:
            os.remove(file_path)
    else:
        await update.message.reply_text("Надішліть PDF файл.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")
    await update.message.reply_text(f"{config.START}", parse_mode='Markdown')


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")
    await update.message.reply_text(f"{config.HELP1}", parse_mode='Markdown')
    await update.message.reply_text(f"{config.HELP2}", parse_mode='Markdown')
    await update.message.reply_text(f"{config.HELP3}", parse_mode='Markdown')
    await update.message.reply_text(f"{config.HELP4}", parse_mode='Markdown')
    await update.message.reply_text(f"{config.HELP5}", parse_mode='Markdown')

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")
    await update.message.reply_text(f"{config.PAY}\n Ваш ID {user.id}", parse_mode='Markdown')



async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")

    status = db.get_user_chat(user.id)
    text = update.message.text
    user_tokens = db.get_user_tokens(user.id)

    if status == 0:
        instruction = instruction_chat
        chat_version = chat_v_4_mini
    else:
        instruction = instruction_test
        chat_version = chat_v_4

    if user_tokens > 0:
        response, tokens_used = send_text_to_chatgpt(text, instruction, chat_version)
        new_balance = user_tokens - tokens_used
        db.update_user_tokens(user.id, new_balance)

        await update.message.reply_text(
            f"Відповідь: {response}\nВикористано токенів: {tokens_used}\n")
    else:
        await update.message.reply_text(
            f"Ваш баланс токенів: {user_tokens}. Потрібно поповнити баланс для продовження.")


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")
    await update.message.reply_text('an error occurred')


async def tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")  # Логування користувача, якщо його ще немає в базі
    user_tokens = db.get_user_tokens(user.id)  # Отримуємо кількість токенів
    await update.message.reply_text(f'У вас є {user_tokens} токенів.')

async def tokens_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 1:
        try:
            user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Будь ласка, введіть правильний ID користувача.")
            return

        user_tokens = db.get_user_tokens(user_id)
        await update.message.reply_text(f'У користувача з ID {user_id} є {user_tokens} токенів.')
    else:
        await update.message.reply_text("Введіть ID користувача після команди /tokens.")
        
async def get_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id == config.PASS_TOKEN:
        list = ""
        
        users = db.get_all_users()
        list += "Користувачі та їх баланс:"
        for user in users:
            list += f"ID: {user[0]}, Ім'я: {user[1]}, Прізвище: {user[2]}, Логін: {user[3]}, Баланс: {user[4]}\n"
        await update.message.reply_text(list)
    else:
        await update.message.reply_text("error")


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")
    user_chat = db.get_user_chat(user.id)
    if user_chat == 0:
        db.update_user_chat(user.id, 1)
        respond = "Встановлено режим вирішування тестів"
    else:
        respond = "У вас вже вибраний режим вирішування тестів"
    await update.message.reply_text(respond)


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    f_t = db.log_user_data(user)
    
    if f_t == 1:
        await context.bot.send_message(chat_id = config.PASS_TOKEN, text=f"Користувач з ID {user.id} вперше зареєструвався!")
    user_chat = db.get_user_chat(user.id)
    if user_chat == 1:
        db.update_user_chat(user.id, 0)
        respond = "Встановлено режим чату"
    else:
        respond = "У вас вже вибраний режим чату"
    await update.message.reply_text(respond)

async def a_t_u(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id == config.PASS_TOKEN:

        if len(context.args) == 2:
            try:
                user_id = int(context.args[0])
                user_pay = int(context.args[1])
            except ValueError:
                await update.message.reply_text("Некоректні аргументи")
                return

            if user_pay > 0:
                k = 350
                if user_pay < 200:
                    user_pay = user_pay * 1.0 * k
                elif user_pay < 500:
                    user_pay = user_pay * 1.1 * k
                else:
                    user_pay = user_pay * 1.2 * k

                user_tokens = db.get_user_tokens(user_id)
                user_tokens = user_tokens + user_pay
                db.update_user_tokens(user_id, user_tokens)

                await update.message.reply_text(f"Успішне зарахування {user_pay} токенів!\nУ користувача з ID {user_id} є {user_tokens} токенів.")
                await context.bot.send_message(chat_id=user_id, text=f"Успішне зарахування {user_pay} токенів!")
            else:
                await update.message.reply_text("Некоректні аргументи")
        else:
            await update.message.reply_text("Некоректні аргументи")
    else:
        await update.message.reply_text("Вау, молодець, надішли мені це повідомлення та отримай бонус")



def main():
    TOKEN = config.TEL_TOKEN
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("tokens", tokens))
    app.add_handler(CommandHandler("tokens_in", tokens_in))
    app.add_handler(CommandHandler("chat", chat))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("a_t_u", a_t_u))
    app.add_handler(CommandHandler("get_users", get_users))

    app.add_handler(MessageHandler(filters.TEXT, text))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    app.add_error_handler(error)

    app.run_polling()


if __name__ == '__main__':
    main()
