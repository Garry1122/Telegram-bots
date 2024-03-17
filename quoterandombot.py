from telebot import types
import requests
import telebot
import json 

DB_PATH = "db.json"
TOKEN = "6922940906:AAH0YGceAEvETXHLemXE_l__OXY1dxPM8Dw"
bot = telebot.TeleBot(TOKEN)

user_lang = {}
@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    if user_id in user_lang:
        del user_lang[user_id]
    bot.send_message(message.chat.id, 'Привет! Я бот, который может отправлять цитаты на английском и русском языке. Пожалуйста, напиши /help для инструкций.\n')
  
@bot.message_handler(commands=['help'])
def help_message(message):
    """
        Modifications: If configuration exists for current chat, notify user about it, and if user want to change
        something than he can click to lang command otherwise he can click quote command and get random quote
    :param message:
    :return: None
    """
    db_exists = is_file_exist(DB_PATH)
    if db_exists:
        bot.send_message(message.chat.id,'''Команды:
    /start - Начать общение с ботом
    /help - Показать это сообщение справки
    /lang - Выбрать язык для цитат
    /quote - Получить случайную цитату
    /history - Посмотреть историю сохраненных цитатa
    /save - Сохранить текущую цитату
    /delete - Удаляет цитату по номеру из списка сохраненных''')
            
    else:
        bot.send_message(message.chat.id,'''Команды:
    /start - Начать общение с ботом
    /help - Показать это сообщение справки
    /lang - Выбрать язык для цитат
    /quote - Получить случайную цитату
    /history - Посмотреть историю сохраненных цитатa
    /save - Сохранить текущую цитату
    /delete - Удаляет цитату по номеру из списка сохраненных''')
        bot.send_message(message.chat.id, "Для начала давай выберим язык.\nВызови команду /lang")

@bot.message_handler(commands=['lang'])
def lang_message(message):
    markup = types.ReplyKeyboardMarkup(row_width=1)
    itembtn1 = types.KeyboardButton('English')
    itembtn2 = types.KeyboardButton('Русский')
    markup.add(itembtn1, itembtn2)
    bot.send_message(message.chat.id, "Выбери язык English или Русский", reply_markup=markup)
    bot.register_next_step_handler(message, set_language)

def set_language(message):
    user_input = message.text.lower()
    chat_configuration = {}
    if user_input in ['английский', 'english']:
        chat_configuration["lang"] = 'en'
    elif user_input in ['русский', 'russian']:
        chat_configuration["lang"] = 'ru'
    else:
        bot.send_message(message.chat.id, "Пожалуйста, выбери English или Русский.")
        return
    
    bot.send_message(message.chat.id, f'Язык установлен на {chat_configuration["lang"]}.')

    save_chat_configuration(chat_id=message.chat.id, chat_configuration=chat_configuration)
    quote_message(message)
# Переменные для хранения последней цитаты
last_quote = {}

# Измененная функция quote_message
@bot.message_handler(regexp='Цитата|Quote|Прислать еще')
def quote_message(message):
    config_db = list(open_json(DB_PATH)["chats_configuration"].keys())
    if str(message.chat.id) not in config_db:
        bot.send_message(message.chat.id, "Выбери язык сначала с помощью команды /lang.")
        return

    lang = open_json(file_path=DB_PATH)["chats_configuration"][str(message.chat.id)]["language"]
    quote = get_random_quote(lang)
    if quote:
        # Сохраняем последнюю присланную цитату
        last_quote[message.chat.id] = quote
        bot.send_message(message.chat.id, f'"{quote["text"]}" - {quote["author"]}')
        markup = types.ReplyKeyboardMarkup(row_width=1)
        itembtn1 = types.KeyboardButton('Прислать еще')
        markup.add(itembtn1)
        bot.send_message(message.chat.id, "Хочешь еще цитату?", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Извини, не удалось получить цитату. Попробуй еще раз.")

# Добавленная команда /save
@bot.message_handler(commands=['save'])
def save_quote_command(message):
    config_db = list(open_json(DB_PATH)["chats_configuration"].keys())
    if str(message.chat.id) not in config_db:
        bot.send_message(message.chat.id, "Выбери язык сначала с помощью команды /lang.")
        return

    # Проверяем, есть ли последняя присланная цитата
    if message.chat.id in last_quote and last_quote[message.chat.id]:
        quote_text = last_quote[message.chat.id]["text"]
        store_in_file_db(chat_id=message.chat.id, message=quote_text)
        bot.send_message(message.chat.id, f'Цитата успешно сохранена: "{quote_text}"')
        # Очищаем последнюю цитату после сохранения
        last_quote[message.chat.id] = None
    else:
        bot.send_message(message.chat.id, "Нет доступных цитат для сохранения.")

def get_random_quote(lang):
    try:
        response = requests.get(f"http://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang={lang}")
        data = response.json()
        return {"text": data.get("quoteText", ""), "author": data.get("quoteAuthor", ""), "lang": lang}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching quote: {e}")
        return None
    
# Реализация сохранения цитат
saved_quotes = {}
last_quote = {}

@bot.message_handler(commands=['history'])
def save_quote(message):
    unique_id = 1
    quotes_history = open_json(file_path=DB_PATH)[str(message.chat.id)]
    for quote in quotes_history:
        bot.send_message(message.chat.id, f'{unique_id}: {quote["message"]}')
        unique_id += 1
        
    if quotes_history == []:
        bot.send_message(message.chat.id, "Список сохраненных цитат пуст")
        
@bot.message_handler(commands=['delete'])
def delete_quote(message):
    bot.send_message(message.chat.id, "Введите номер цитаты, которую вы хотите удалить.")
    bot.register_next_step_handler(message, delete_quote_by_number)

def delete_quote_by_number(message):
    try:
        quote_number = int(message.text)
        chat_id = str(message.chat.id)

        with open(DB_PATH, 'r') as f:
            data = json.load(f)

        if chat_id in data and "chats_configuration" in data and chat_id in data["chats_configuration"]:
            chat_config = data["chats_configuration"][chat_id]

            if "language" in chat_config and chat_id in data and quote_number <= len(data[chat_id]):
                del data[chat_id][quote_number - 1]  # Исправлено, чтобы учитывать индексацию с 0
                with open(DB_PATH, 'w') as f:
                    json.dump(data, f, indent=4)
                bot.send_message(message.chat.id, f"Цитата номер {quote_number} была успешно удалена.")
            else:
                bot.send_message(message.chat.id, "Цитаты с таким номером не существует. Пожалуйста, введите действительный номер цитаты.")
        else:
            bot.send_message(message.chat.id, "Не удалось получить конфигурацию чата. Пожалуйста, попробуйте еще раз.")
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите номер цитаты цифрой.")


def is_file_exist(file_path):
    try:
        open_json(file_path)
        return True
        
    except FileNotFoundError:
        return False

def save_chat_configuration(chat_id, chat_configuration):
    """
        Saves Chat configuration in the db file for further usage in thi format
        {
            "chat_id": {
                "language": "en",
                "other_setting": "other_value"
            }
        }
        :param chat_id: Chat id of selected chat
        :param chat_configuration: dict with chatbot configuration
        :return: None
    """
    file_exist = is_file_exist(DB_PATH)
    if not file_exist:
        with open(DB_PATH, "w") as json_file:
            json.dump(
                {
                    "chats_configuration": {
                        chat_id: {
                            "language": chat_configuration.get("lang")
                        }
                    }
                }
            , json_file, ensure_ascii=False, indent=4)
    else:
        db_file: dict = open_json(DB_PATH)
        if db_file.get(chat_id):
            db_file["chats_configuration"][chat_id]["language"] = chat_configuration.get("lang")
        else:
            db_file["chats_configuration"] = {
                        chat_id:{
                            "language": chat_configuration.get("lang")
                    }
            }
        save_json(json_file=db_file, file_path=DB_PATH)

def store_in_file_db(chat_id, message):
    chat_id = str(chat_id)
    
    file_exist = is_file_exist(DB_PATH)

    if not message and not chat_id:
        return

    if not file_exist:
        with open(DB_PATH, "w") as json_file:
            json.dump(
                {
                    chat_id: [
                        {"unique_id": 1, "message": message},
                    ]
                }
            , json_file, ensure_ascii=False, indent=4)
    else:
        db_file: dict = open_json(DB_PATH)
        
        if db_file.get(chat_id):
            unique_id = len(db_file[chat_id]) + 1
            db_file[chat_id].append({"unique_id": unique_id, "message": message})
        else:
            db_file[chat_id] = [{"unique_id": 1, "message": message}]
        
        save_json(DB_PATH, db_file)

def open_json(file_path) -> dict:
     with open(file_path, "r") as json_file:
            return json.load(json_file)
        
def save_json(file_path, json_file):
    with open(file_path, 'w') as f:
        json.dump(json_file, f, indent=4)

def check_config_existence(chat_id):
    config_db = list(open_json(DB_PATH)["chats_configuration"].keys())
    if str(chat_id) not in config_db:
        return False
    return True

# Запуск бота
bot.polling()
