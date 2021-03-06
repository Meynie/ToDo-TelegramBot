import json
import requests
import time
import urllib

from config import URL
from dbhelper import DBHelper

db = DBHelper()


# Загружает контент с URL и даёт строку
def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content


# Функция получает строковый ответ и анализирует, используя json.load()
def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js


def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = get_json_from_url(url)
    return js


def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


def get_last_chat_id_and_text(updates):
    """
    Полуаю идентификатор пользователя
    """
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)


def handler_updates(updates):
    """
    Просмотр всех сообщений и ответ.
    Включает загрузку всех элементов из БД и хранение их в tems.
    """
    for update in updates["result"]:
        text = update["message"]["text"]
        chat = update["message"]["chat"]["id"]
        items = db.get_items(chat)
        if text == '/done':
            keyboard = build_keyboard(items)
            send_message("Select an item to delete", chat, keyboard)
        elif text == '/start':
            send_message("Welcome to your personal To Do list. Send any text to me and I\'ll store it as an item. Send /done to remove items", chat)
        elif text in items: # Если такое сообщение уже было, то удаляю
            db.delete_item(text, chat)
            items = db.get_items(chat)
            keyboard = build_keyboard(items)
            send_message("Select an item to delete", chat, keyboard)
        elif text.startswith("/"):
            continue
        else:
            db.add_item(text, chat) # Если сообщение новое, то добавляю
            items = db.get_items(chat)
            message = "\n".join(items) # Всегда отправляется сообщение, где каждый сохраненный элемент в новой строке
            send_message(message, chat)


def build_keyboard(items):
    """
    Создаёт список элементов, превращая каждый элемент в список,
    делая строкой клавиатуры keyboard.
    Словарь содержит эту клавиатуру, которая исчезнет после нажатия кнопки.
    """
    keyboard = [[item] for item in items]
    reply_markup = {'keyboard': keyboard, "one_time_keyboard": True}
    return json.dumps(reply_markup)


def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text) # Обработка специальных символов
    url = URL + "sendMessage?text={}&chat_id={}".format(text, chat_id)
    if reply_markup: # Если клавиатура включена, то она передастся вместе с остальной частью вызова API
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)


def main():
    db.setup()
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            handler_updates(updates)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
