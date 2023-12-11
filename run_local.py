# включить после выключения
import configparser
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DELETE_LAST_DIR = True

config = configparser.ConfigParser()
config.read('configs/Default.ini')
config.set("Default", "reload", "True")
with open('configs/Default.ini', 'w') as configfile:
        config.write(configfile)

# === Обязательные настройки ===
# API ключ дискорд бота (брать тут https://discord.com/developers/applications)
discord_api = "MTE..."
# агрументы для запуска.
# gpt_local - локальный GPT (плохой)
# img1 - использовать 1 видеокарту для изображений
# img2 - использовать 2 видеокарты для изображений
# None - не использовать видеокарты для изображений
mode_running = "img1"

# ===Дополнительные настройки===
# голосовая модель
url = "https://huggingface.co/TJKAI/TomHolland/resolve/main/TomHolland.zip" # введите ссылку на RVC модель (https://voice-models.com/)
dir_name = "Холланд" #  введите имя модели (без пробелов!)
gender = "male" # введите пол (male, female)
info = "Том Холланд (родился 1 июня 1996 года) — английский актёр. Широкую известность получил после исполнения роли Человека-паука в кинематографической вселенной Marvel." # информация о человеке (для ChatGPT)
voice_model = "Adam" # модель elevenlab (список: https://elevenlabs.io/speech-synthesis). Рекомендую: 'Harry', 'Arnold', 'Clyde', 'Thomas', 'Adam', 'Antoni', 'Daniel', 'Harry', 'James', 'Patrick'
speed = "1.1" # насколько будет ускоряться голос (1.5 - на 50% быстрее, 1 - обычная скорость)
# выставляем ключи для TTS (брать тут - elevenlabs.io)
elevenlabs_api_keys = ';'.join(["Free", "Ваш ключ1", "Ваш ключ2"])
# добавляем cookie с сайта-провайдера (впишите выход команды JSON.stringify(document.cookie.split('; ').map(c => c.split('=')).reduce((c, [k, v]) => ({ ...c, [k]: v }), {})))
cookies = '{"ключ":"значение"}'
# ваш UserID в дискорде
user_id_owner = "Ваш USER ID"
# API ключ от ПЛАТНОГО аккуанта OpenAI (для GPT-4)
gpt4_api = "None" # sk-xxxxxxxxxxxxxxxx
# accessToken. БЕСПЛАТНО получить можно тут: https://chat.openai.com/api/auth/session
accessToken = "eyJh...."


import shutil
import json

config = configparser.ConfigParser()

while True:
    user_id = "True"
    if os.path.exists('ds_ai') and DELETE_LAST_DIR:
        os.chdir('ds_ai')
        config.read('configs\\Default.ini')
        user_id = config.get("Default", "reload")
        print("RELOAD:", user_id)
        if user_id == "False":
            break

        os.chdir(BASE_DIR)
        shutil.rmtree('ds_ai')

    os.chdir(BASE_DIR)

    # Клонирование репозитория
    os.system('git clone https://github.com/Badim41/ds_ai.git')
    os.chdir('ds_ai')

    # Клонирование discord из pycord
    os.system('git clone https://github.com/Pycord-Development/pycord.git')
    shutil.move("pycord\\discord", "discord")
    shutil.rmtree('pycord')

    # Скачивание моделей RVC, UVR5, huber_base
    os.system('python download_models.py')

    # Настройка RVC
    config.read('configs\\Default.ini')
    config.set("Default", "currentainame", dir_name)
    if gender == "female":
        pitch = "12"
    else:
        pitch = "0"
    config.set("Default", "currentaipitch", pitch)
    config.set("Default", "currentaiinfo", info)
    with open('configs\\Default.ini', 'w') as configfile:
        config.write(configfile)

    config.read('configs\\Sound.ini')
    config.set("Default", "voices", f"None;{dir_name}")
    with open('configs\\Sound.ini', 'w') as configfile:
        config.write(configfile)

    # Загрузка голосовой модели
    os.system(f'python download_voice_model.py {url} {dir_name} {gender} f"{info}" {voice_model} {speed}')

    # Настройка elevenlabs API_keys
    config.read('configs\\voice.ini')
    config.set("Default", "avaible_keys", elevenlabs_api_keys)
    with open('configs\\voice.ini', 'w') as configfile:
        config.write(configfile)

    # Установка cookies
    if not cookies == "None":
        data = json.loads(cookies)
        with open('cookies.json', 'w') as file:
            json.dump(data, file, indent=4)

    # Отправка сообщения о перезагрузке
    if not user_id_owner == "Ваш USER ID":
        user_id = user_id_owner
    config.read('configs\\Default.ini')
    config.set("Default", "owner_id", user_id_owner)
    config.set("Default", "reload", user_id)
    with open('configs\\Default.ini', 'w') as configfile:
        config.write(configfile)
    config.read('configs\\gpt.ini')
    config.set("Default", "avaible_keys", gpt4_api)
    config.set("Default", "auth_key", accessToken)
    with open('configs\\gpt.ini', 'w') as configfile:
        config.write(configfile)

    # Запуск бота
    os.system(f'python discord_bot.py {discord_api} {mode_running}')