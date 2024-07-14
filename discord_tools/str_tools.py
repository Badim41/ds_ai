import base64
import hashlib
import json
import random
import re
import string

import urllib
from urllib.parse import urlparse, parse_qs


def convert_answer_to_json(answer, keys, start_symbol="{", end_symbol="}", attemtp=1):
    if isinstance(keys, str):
        keys = [keys]

    answer = answer.replace(" ", "")

    if attemtp == 2:
        if start_symbol in answer and end_symbol in answer:
            answer = answer[answer.find(start_symbol):]
            answer = answer[:answer.find(end_symbol) + 1]
        else:
            print("Не json")
            return False, "Не json"
    elif attemtp == 1:
        if start_symbol in answer and end_symbol in answer:
            answer = answer[answer.find(start_symbol):]
            answer = answer[:answer.rfind(end_symbol) + 1]
        else:
            print("Не json")
            return False, "Не json"
    else:
        return False, "ERROR"

    try:
        response = json.loads(answer)
        for key in keys:
            if response.get(key, "NULL_VALUE") == "NULL_VALUE":
                print("Нет ключа")
                return False, "Нет ключа"
        return True, response
    except json.JSONDecodeError as e:
        print("Error", e)
        return convert_answer_to_json(answer=answer, keys=keys, start_symbol=start_symbol, end_symbol=end_symbol, attemtp=attemtp+1)


def remove_emojis(text):
    # Паттерн для поиска смайликов
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # смайлики эмодзи
                               u"\U0001F300-\U0001F5FF"  # символы и пиктограммы
                               u"\U0001F680-\U0001F6FF"  # символы транспорта и карты
                               u"\U0001F1E0-\U0001F1FF"  # флаги (iOS)
                               "]+", flags=re.UNICODE)
    # Удаляем смайлики из текста
    return emoji_pattern.sub(r'', text)

def extract_urls(text):
    # Регулярное выражение для поиска URL в тексте
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

    # Используем регулярное выражение для поиска всех URL в тексте
    urls = re.findall(url_pattern, text)

    return urls

def get_cookie_dict_from_response(response):
    cookies = response.cookies
    cookie_dict = {cookie.name: cookie.value for cookie in cookies}
    return cookie_dict

def create_query_dict_from_url(url):
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        query_dict = {}
        for param, value in query_params.items():
            query_dict[param] = value[0]

        return query_dict


def create_cookies_dict(cookies_str):
    if isinstance(cookies_str, dict):
        return cookies_str
    elif isinstance(cookies_str, str):
        # Разделяем строку по точке с запятой, чтобы получить список cookie-пар
        cookies = cookies_str.split('; ')

        # Создаем словарь для хранения cookie
        cookie_dict = {}

        # Проходим по списку cookie-пар
        for cookie in cookies:
            # Разделяем каждую пару на ключ и значение
            key, value = cookie.split('=', 1)
            # Добавляем ключ и значение в словарь
            cookie_dict[key] = value

        return cookie_dict

    raise Exception("cookie должны быть str или dict")

def create_queue_params_dict_from_url(url):
    parsed_url = urlparse(url)
    queue_params = parse_qs(parsed_url.query)
    for key in queue_params:
        queue_params[key] = queue_params[key][0]
    return queue_params

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def random_string(length=8, seed=None, input_str=None):
    if not input_str is None:
        # Создаем хэш входной строки
        hash_object = hashlib.sha256(input_str.encode())
        hash_hex = hash_object.hexdigest()
        # Инициализируем генератор случайных чисел на основе хэша
        random.seed(hash_hex)
    elif not seed is None:
        random.seed(seed)
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))