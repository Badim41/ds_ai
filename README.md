[![Discord](https://img.shields.io/badge/-Discord-5865F2?logo=discord&logoColor=white)]([https://discord.com/](https://discord.gg/nuUWVR2WzR)) <sup><strong>Сервер в Discord</strong></sup>
[![Telegram](https://img.shields.io/badge/-Telegram-26A5E4?logo=telegram&logoColor=white)]([https://telegram.org/](https://t.me/GPT4_Unlimit_bot?start=2)) <sup><strong>Бот в Telegram</strong></sup>

> [!Note]
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/) <sup><strong>Неполный функционал (GPT + Kondinski)</strong></sup>

> [!Note]
[![Kaggle](https://img.shields.io/badge/-Kaggle-20BEFF?logo=kaggle&logoColor=white)](https://www.kaggle.com/) <sup><strong>Полный функционал (RVC + GPT + Kondinski)</strong></sup> 

Discord-бот для использования ИИ
1. [Описание](#section-1)
2. [Основные библиотеки](#section-2)
3. [Возможности](#section-3)
4. [Установка](#section-4)
   
   4.1 [Linux](#section-4.1)
   
   4.2 [Windows](#section-4.2)
   
   4.3 [Обязательные аргументы](#section-4.3)
   
   4.4 [Необязательные аргументы](#section-4.4)
   
6. [Помощь](#section-5)

Репозитории, из которых взята часть кода:

https://github.com/ai-forever/Kandinsky-2                                
https://github.com/SociallyIneptWeeb/AICoverGen                                
https://github.com/xtekky/gpt4free

## Описание проекта <a name="section-1"></a>

### Основные библиотеки <a name="section-2"></a>

- `py-cord`: Для работы с Discord API, обеспечивает асинхронные функции и поддержку слэш-команд.
- `torch`: Используется для работы с видеокартой, в данном случае - для работы с RVC.
- `g4f`: Библиотека для бесплатных запросов к ChatGPT.
- `openai`: Используется для платных запросов к ChatGPT.
- `elevenlabs`: Для озвучивания текста с помощью нейронных сетей.
- `gTTS`: Для озвучивания текста.
- `SpeechRecognition`: Инструмент для распознавания речи

### Основные возможности бота <a name="section-3"></a>

Основные функции бота включают в себя:

- Генерация текста (GPT-3.5, GPT-4).
- Генерация и изменение картинок (Kondinski)
- Изменение голоса в аудиофайлах (RVC, UVR5).
- Создание диалогов (GPT-3.5, RVC).
- Озвучивание текстовых сообщений (Elevenlabs, RVC).

## Установка и настройка <a name="section-4"></a>
**Необходима версия Python - 3.9**
### Linux <a name="section-4.1"></a>

Клонирование репозитория

```sh
git clone https://github.com/Badim41/ds_ai.git
```
```sh
cd ds_ai
```

Установка зависимостей

```sh
sudo apt update -y
sudo apt install -y portaudio19-dev
pip install -r requirements.txt
pip install -r requirements2.txt
sudo apt install sox -y
sudo apt-get install rubberband-cli
```

### Windows <a name="section-4.2"></a>

Клонирование репозитория

```sh
git clone https://github.com/Badim41/ds_ai.git
```
```sh
cd ds_ai
```

Установка зависимостей

```sh
pip install -r requirements.txt
pip install -r requirements2.txt
```

## Установка Git и Python 3.9

Установка Git [тут](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) 

Установка **Python 3.9** [тут](https://realpython.com/installing-python/)

### Установка ffmpeg

Инструкция [тут](https://www.hostinger.com/tutorials/how-to-install-ffmpeg) для установки ffmpeg

### Установка sox

Инструкция [тут](https://www.tutorialexample.com/a-step-guide-to-install-sox-sound-exchange-on-windows-10-python-tutorial/) для установки sox

**Также установите и добавьте в PATH Sox и ffmpeg**

## Обязательные настройки <a name="section-4.3"></a>

```python
# API ключ дискорд бота (брать тут https://discord.com/developers/applications)
discord_api = "MTE..."
агрументы для запуска.
# gpt_local - локальный GPT (плохой)
# img1 - использовать 1 видеокарту для изображений
# img2 - использовать 2 видеокарты для изображений
# None - не использовать видеокарты для изображений
mode_running = "img1"
```

### Необязательные настройки <a name="section-4.4"></a>

```python
# Предустановленная голосовая модель
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
```

### Вопросы и обратная связь <a name="section-5"></a>

Если у вас есть ошибки, вопросы, предложения, создайте вопрос в issue

