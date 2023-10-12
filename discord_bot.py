import multiprocessing
import os
import random
import struct
import subprocess
import configparser
import asyncio
import wave

from pydub import AudioSegment

from discord import Option
from modifed_sinks import StreamSink
import speech_recognition as sr
from pathlib import Path
import sys
import discord
from discord.ext import commands

# Значения по умолчанию
voiceChannelErrorText = '❗ Вы должны находиться в голосовом канале ❗'
config = configparser.ConfigParser()

connections = {}

stream_sink = StreamSink()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='\\', intents=intents)


async def set_get_config_all(section, key, value):
    config.read('config.ini')
    if value is None:
        config.read('config.ini')
        return config.get(section, key)
    config.set(section, key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
    return ' '.join([section, key, str(value)])


async def set_get_config(key="record", value=None):
    config.read('config.ini')
    if value is None:
        config.read('config.ini')
        return config.get("Sound", key)
    config.set('Sound', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


async def set_get_config_default(key, value=None):
    config.read('config.ini')
    if value is None:
        config.read('config.ini')
        return config.get("Default", key)
    config.set('Default', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


@bot.event
async def on_ready():
    print('Status: online')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name='AI-covers'))


# @bot.event
# async def on_message(message):
#     if message.author.bot:
#         return
#     if len(message.attachments) > 0:
#         for attachment in message.attachments:
#             await attachment.save(attachment.filename)
#             print(f'Получен файл: {attachment.filename}')


@bot.slash_command(name="change_image", description='изменить изображение нейросетью')
async def __image(ctx,
                  image: Option(discord.SlashCommandOptionType.attachment, description='Изображение',
                                required=True),
                  # prompt=prompt, negative_prompt=negative_prompt, x=512, y=512, steps=50,
                  #                      seed=random.randint(1, 10000), strenght=0.5
                  prompt: Option(str, description='запрос', required=True),
                  negative_prompt: Option(str, description='негативный запрос', default="NSFW", required=False),
                  steps: Option(int, description='число шагов', required=False,
                                default=30,
                                min_value=1,
                                max_value=500),
                  seed: Option(int, description='сид изображения', required=False,
                               default=random.randint(1, 1000000),
                               min_value=1,
                               max_value=1000000),
                  strength: Option(float, description='насколько сильны будут изменения', required=False,
                                   default=0.5, min_value=0,
                                   max_value=1),
                  strength_prompt: Option(float,
                                          description='ЛУЧШЕ НЕ ТРОГАТЬ! Насколько сильно генерируется положительный промпт',
                                          required=False,
                                          default=0.85, min_value=0,
                                          max_value=1),
                  strength_negative_prompt: Option(float,
                                                   description='ЛУЧШЕ НЕ ТРОГАТЬ! Насколько сильно генерируется отрицательный промпт',
                                                   required=False,
                                                   default=1, min_value=0,
                                                   max_value=1)
                  ):
    await set_get_config_all("Image", "result", "None")
    await ctx.defer()
    if await set_get_config_all("Image", "model_loaded", None) == "False":
        return await ctx.respond("модель для картинок не загрузилась, подождите 10-20 минут")
    filename = str(random.randint(1, 1000000)) + ".png"
    await image.save(filename)
    # get image size and round to 64
    x, y = await get_image_dimensions(filename)
    if not x % 64 == 0:
        x = ((x // 64) + 1) * 64
    if not y % 64 == 0:
        y = ((y // 64) + 1) * 64
    # loading params
    await set_get_config_all("Image", "strength_negative_prompt", strength_negative_prompt)
    await set_get_config_all("Image", "strength_prompt", strength_prompt)
    await set_get_config_all("Image", "strength", strength)
    await set_get_config_all("Image", "seed", seed)
    await set_get_config_all("Image", "steps", steps)
    await set_get_config_all("Image", "negative_prompt", negative_prompt)
    await set_get_config_all("Image", "prompt", prompt)
    await set_get_config_all("Image", "x", x)
    await set_get_config_all("Image", "y", y)
    await set_get_config_all("Image", "input", filename)
    print("params suc")
    # wait for answer
    image_path = await set_get_config_all("Image", "result", None)
    while image_path == "None":
        image_path = await set_get_config_all("Image", "result", None)
        await asyncio.sleep(0.25)
    await ctx.respond("Вот как я изменил ваше изображение🖌")
    await send_file(ctx, image_path)


@bot.slash_command(name="config", description='изменить конфиг (лучше не трогать, если не знаешь!)')
async def __config(
        ctx,
        section: Option(str, description='секция', required=True),
        key: Option(str, description='ключ', required=True),
        value: Option(str, description='значение', required=False, default=None)
):
    await ctx.defer()
    await ctx.respond(await set_get_config_all(section, key, value))


@bot.slash_command(name="join", description='присоединиться к голосовому каналу')
async def join(ctx):
    await ctx.defer()
    voice = ctx.author.voice
    if not voice:
        await ctx.respond(voiceChannelErrorText)
        return

    voice_channel = voice.channel

    if ctx.voice_client is not None:
        return await ctx.voice_client.move_to(voice_channel)

    await voice_channel.connect()
    await ctx.respond("присоединяюсь")


@bot.slash_command(name="record", description='воспринимать команды из микрофона')
async def record(ctx):  # if you're using commands.Bot, this will also work.
    voice = ctx.author.voice
    voice_channel = voice.channel
    # добавляем ключ к connetions
    if ctx.guild.id not in connections:
        connections[ctx.guild.id] = []

    if not voice:
        return await ctx.respond(voiceChannelErrorText)

    if ctx.voice_client is None:
        # если бота НЕТ в войс-чате
        vc = await voice_channel.connect()
    else:
        # если бот УЖЕ в войс-чате
        vc = ctx.voice_client
    # если уже записывает
    if vc in connections[ctx.guild.id]:
        return await ctx.respond("Уже записываю ваш голос🎤")
    stream_sink.set_user(ctx.author.id)
    connections[ctx.guild.id].append(vc)

    # Начинаем запись
    vc.start_recording(
        stream_sink,  # the sink type to use.
        once_done,  # what to do once done.
        ctx.channel  # the channel to disconnect from.
    )
    await set_get_config(value=True)
    await ctx.respond("Started listening.")
    await recognize(ctx)


@bot.slash_command(name="stop_recording", description='перестать воспринимать команды из микрофона')
async def stop_recording(ctx):
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id][0]  # Получаем элемент списка
        vc.stop_recording()
        del connections[ctx.guild.id]
    else:
        await ctx.respond("Я и так тебя не слушал ._.")


@bot.slash_command(name="disconnect", description='выйти из войс-чата')
async def disconnect(ctx):
    await ctx.defer()
    voice = ctx.voice_client
    if voice:
        await voice.disconnect(force=True)
        await ctx.respond("выхожу")
    else:
        await ctx.respond("Я не в войсе")
    if ctx.guild.id in connections:
        del connections[ctx.guild.id]  # remove the guild from the cache.


# @bot.command(help="сказать роботу текст")
# async def say(ctx, *args):
#     message = " ".join(args)
#     from function import replace_mat_in_sentence
#     if not default_settings.get("robot_name_need"):
#         message = default_settings.get("currentAIname") + ", " + message
#         print(message)
#     else:
#         print(message)
#     message = await replace_mat_in_sentence(message)
#     # Проверяем, находится ли автор команды в войс-чате
#     # if ctx.author.voice:
#     if True:
#         # Получаем войс-канал автора команды
#         # voice_channel = ctx.author.voice.channel
#         # # Проверяем, находится ли бот уже в каком-либо войс-чате
#         # if ctx.voice_client is None:
#         #     # Если бот не находится в войс-чате, подключаем его
#         #     await voice_channel.connect()
#         # else:
#         #     # Если бот уже находится в войс-чате, перемещаем его в новый войс-канал
#         #     await ctx.voice_client.move_to(voice_channel)
#         await run_main_with_settings(ctx, message, True)
#     else:
#         await ctx.send("Вы должны находиться в войс-чате, чтобы использовать эту команду.")


@bot.slash_command(name="pause", description='пауза/воспроизведение')
async def pause(ctx):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.respond("Пауза ⏸")
    elif voice_client.is_paused():
        voice_client.resume()
        await ctx.respond("Продолжаем воспроизведение ▶️")
    else:
        await ctx.respond("Нет активного аудио для приостановки или продолжения.")


@bot.slash_command(name="skip", description='пропуск аудио')
async def skip(ctx):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    voice_client = ctx.voice_client
    if voice_client.is_playing():
        voice_client.stop()
        await ctx.respond("Текущий трек пропущен ⏭️")
        await set_get_config("stop_milliseconds", 0)
    else:
        await ctx.respond("Нет активного аудио для пропуска.")


@bot.slash_command(name="lenght", description='Длина запроса')
async def __lenght(
        ctx,
        number: Option(int, description='Длина запроса для GPT (Число от 1 до 1000)', required=True, min_value=1,
                       max_value=1000)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    # for argument in (number,"""boolean, member, text, choice"""):
    print(f'{number} ({type(number).__name__})\n')
    await run_main_with_settings(ctx, f"робот длина запроса {number}", True)
    await ctx.respond(f"Длина запроса: {number}")


@bot.slash_command(name="say", description='Сказать роботу что-то')
async def __say(
        ctx,
        text: Option(str, description='Сам текст/команда. Список команд: \\help-say', required=True)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    from function import replace_mat_in_sentence
    if await set_get_config_default("robot_name_need") == "False":
        text = await set_get_config_default("currentainame") + ", " + text
    text = await replace_mat_in_sentence(text)
    print(f'{text} ({type(text).__name__})\n')
    await run_main_with_settings(ctx, text, True)


@bot.slash_command(name="tts", description='_Заставить_ бота говорить всё, что захочешь')
async def __tts(
        ctx,
        text: Option(str, description='Текст для озвучки', required=True),
        ai_voice: Option(str, description='Голос для озвучки', required=False, default="None")
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    config.read('config.ini')
    voices = config.get("Sound", "voices").replace("\"", "").replace(",", "").split(";")
    if ai_voice not in voices:
        return await ctx.respond("Выберите голос из списка: " + ','.join(voices))
    from function import replace_mat_in_sentence, mat_found
    text = await replace_mat_in_sentence(text)
    if mat_found:
        await ctx.respond("Такое нельзя произносить!")
        return
    print(f'{text} ({type(text).__name__})\n')
    # меняем голос
    ai_voice_temp = await set_get_config_default("currentainame")
    if ai_voice == "None":
        ai_voice = await set_get_config_default("currentainame")
        print(await set_get_config_default("currentainame"))
    await set_get_config_default("currentainame", ai_voice)
    # запускаем TTS
    await run_main_with_settings(ctx, f"робот протокол 24 {text}",
                                 False)  # await text_to_speech(text, False, ctx, ai_dictionary=ai_voice)
    # возращаем голос
    await set_get_config_default("currentainame", ai_voice_temp)


@bot.slash_command(name="ai_cover", description='_Заставить_ бота озвучить видео/спеть песню')
async def __cover(
        ctx,
        url: Option(str, description='Ссылка на видео', required=False),
        audio_path: Option(discord.SlashCommandOptionType.attachment, description='Аудиофайл',
                      required=False),
        voice: Option(str, description='Голос для видео', required=False, default=None),
        pitch: Option(str, description='Кто говорит/поёт в видео?', required=False,
                      choices=['мужчина', 'женщина'], default=None),
        time: Option(int, description='Ограничить длительность воспроизведения (в секундах)', required=False,
                     default=-1, min_value=0),
        indexrate: Option(float, description='Индекс частоты (от 0 до 1)', required=False, default=0.5, min_value=0,
                          max_value=1),
        loudness: Option(float, description='Громкость шума (от 0 до 1)', required=False, default=0.2, min_value=0,
                         max_value=1),
        main_vocal: Option(int, description='Громкость основного вокала (от -20 до 0)', required=False, default=0,
                           min_value=-20, max_value=0),
        back_vocal: Option(int, description='Громкость бэквокала (от -20 до 0)', required=False, default=0,
                           min_value=-20, max_value=0),
        music: Option(int, description='Громкость музыки (от -20 до 0)', required=False, default=0, min_value=-20,
                      max_value=0),
        roomsize: Option(float, description='Размер помещения (от 0 до 1)', required=False, default=0.2, min_value=0,
                         max_value=1),
        wetness: Option(float, description='Влажность (от 0 до 1)', required=False, default=0.1, min_value=0,
                        max_value=1),
        dryness: Option(float, description='Сухость (от 0 до 1)', required=False, default=0.85, min_value=0,
                        max_value=1),
        start: Option(int, description='Начать воспроизводить с (в секундах)', required=False, default=0, min_value=0),
        output: Option(bool, description='Отправить результат в архиве', required=False, default=False)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    params = []
    if audio_path:
        filename = str(random.randint(1, 1000000)) + ".mp3"
        await audio_path.save(filename)
        params.append(f"-url {filename}")
    elif url:
        params.append(f"-url {url}")
    else:
        return ctx.respond('Не указана ссылка или аудиофайл')
    if voice is None:
        voice = await set_get_config_default("currentAIname")
    if voice:
        params.append(f"-voice {voice}")
    # если мужчина-мужчина, женщина-женщина, pitch не меняем
    pitch_int = 0
    # если женщина, но AI мужчина = 1,
    if pitch == 'женщина':
        if not await set_get_config_default("currentaipitch") == 1:
            pitch_int = 1
    # если мужчина, но AI женщина = -1,
    elif pitch == 'мужчина':
        if not await set_get_config_default("currentaipitch") == 0:
            pitch_int = -1
    params.append(f"-pitch {pitch_int}")
    if time != -1:
        params.append(f"-time {time}")
    if indexrate != 0.5:
        params.append(f"-indexrate {indexrate}")
    if loudness != 0.2:
        params.append(f"-loudness {loudness}")
    if main_vocal != 0:
        params.append(f"-vocal {main_vocal}")
    if back_vocal != 0:
        params.append(f"-bvocal {back_vocal}")
    if music != 0:
        params.append(f"-music {music}")
    if roomsize != 0.2:
        params.append(f"-roomsize {roomsize}")
    if wetness != 0.1:
        params.append(f"-wetness {wetness}")
    if dryness != 0.85:
        params.append(f"-dryness {dryness}")
    if start != 0:
        params.append(f"-start {start}")
    param_string = ' '.join(params)

    await run_main_with_settings(ctx, "робот протокол 13 " + param_string, False)
    # output..


@bot.slash_command(name="add_voice", description='Добавить RVC голос')
async def __add_voice(
        ctx,
        url: Option(str, description='Ссылка на .zip файл с моделью RVC', required=True),
        name: Option(str, description=f'Имя модели', required=True),
        gender: Option(str, description=f'Пол (для настройки тональности)', required=True,
                       choices=['мужчина', 'женщина']),
        info: Option(str, description=f'(необязательно) Какие-то сведения о данном человеке', required=False,
                     default="Отсутствует"),
        change_voice: Option(bool, description=f'(необязательно) Изменить голос на этот', required=False,
                             default=False)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    # !python download_model_with_link_AICoverGen.py {url} {dir_name} {gender} {info}
    command = None
    if gender == "женщина":
        gender = "female"
    elif gender == "мужчина":
        gender = "male"
    else:
        gender = "male"
    try:
        command = [
            "python",
            "download_model_with_link_AICoverGen.py",
            url,
            name,
            gender,
            info
        ]
        subprocess.run(command, check=True)
        config.read('config.ini')
        voices = config.get("Sound", "voices").split(";")
        voices.append(name)
        config.set('Sound', "voices", ';'.join(voices))
        # Сохранение
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        if change_voice:
            await run_main_with_settings(ctx, f"робот измени голос на {name}", True)
    except subprocess.CalledProcessError as e:
        await ctx.respond(f"Ошибка при скачивании голоса {command}: {e}")


@bot.command(aliases=['cmd'], help="командная строка")
async def command_line(ctx, *args):
    text = " ".join(args)
    try:
        process = subprocess.Popen(text, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        for line in stdout.decode().split('\n'):
            if line.strip():
                await ctx.send(line)
        for line in stderr.decode().split('\n'):
            if line.strip():
                await ctx.send(line)
    except subprocess.CalledProcessError as e:
        await ctx.send(f"Ошибка выполнения команды: {e}")
    except Exception as e:
        await ctx.send(f"Произошла неизвестная ошибка: {e}")


@bot.command(aliases=['прослушай_кеклола'], help="ХАВХВАХВАХВАХВАХ")
async def i_hear_you(ctx):  # if you're using commands.Bot, this will also work.
    await ctx.send("Получаю базу данных пользователей")
    await asyncio.sleep(1)
    await ctx.send("Пользователь <@920404602317324388> найден!")
    await asyncio.sleep(1)
    await ctx.send("Получен аудиопоток микрофона!")


async def run_main_with_settings(ctx, spokenText, writeAnswer):
    from function import start_bot
    await start_bot(ctx, spokenText, writeAnswer)


async def write_in_discord(ctx, text):
    # await run_main_with_settings(ctx, text, True)
    await ctx.send(text)


async def send_file(ctx, file_path):
    try:
        await ctx.send(file=discord.File(file_path))
    except FileNotFoundError:
        await ctx.send('Файл не найден.')
    except discord.HTTPException:
        await ctx.send('Произошла ошибка при отправке файла.')


async def playSoundFileDiscord(ctx, audio_file_path, duration, start_seconds):
    # Проверяем, находится ли бот в голосовом канале
    if not ctx.voice_client:
        await ctx.send("Бот не находится в голосовом канале. Используйте команду `join`, чтобы присоединить его.")
        return

    # Проверяем, играет ли что-то уже
    if ctx.voice_client.is_playing():
        await asyncio.sleep(0.1)

    # проигрываем
    source = discord.FFmpegPCMAudio(audio_file_path, options=f"-ss {start_seconds} -t {duration}")
    ctx.voice_client.play(source)

    # Ожидаем окончания проигрывания
    while ctx.voice_client.is_playing():
        await asyncio.sleep(1)
        # stop_milliseconds += 1000
        await set_get_config("stop_milliseconds", int(await set_get_config("stop_milliseconds")) + 1000)


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    await set_get_config(value=False)
    # await sink.vc.disconnect()  # disconnect from the voice channel.
    print("Stopped listening.")


file_not_found_in_raw = 0


async def recognize(ctx):
    global file_not_found_in_raw
    wav_filename = "out_all.wav"
    recognizer = sr.Recognizer()
    while True:
        # распознаём, пока не произойдёт once_done
        if await set_get_config() == "False":
            print("Stopped listening2.")
            return
        file_found = None
        # проверяем наличие временных файлов
        for filename in os.listdir(os.getcwd()):
            if filename.startswith("output") and filename.endswith(".wav"):
                file_found = filename
                break
        if file_found is None:
            await asyncio.sleep(0.1)
            file_not_found_in_raw += 1
            # если долго не было файлов (человек перестал говорить)
            if file_not_found_in_raw > float(await set_get_config("delay_record")) * 10:
                text = None
                # очищаем поток
                stream_sink.cleanup()
                file_not_found_in_raw = 0
                # распознание речи
                try:
                    with sr.AudioFile(wav_filename) as source:
                        audio_data = recognizer.record(source)
                        text = recognizer.recognize_google(audio_data, language="ru-RU")
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    print(f"Ошибка при распознавании: {e}")
                # удаление out_all.wav
                try:
                    Path(wav_filename).unlink()
                except FileNotFoundError:
                    pass

                # создание пустого файла
                empty_audio = AudioSegment.silent(duration=0)
                try:
                    empty_audio.export(wav_filename, format="wav")
                except Exception as e:
                    print(f"Ошибка при создании пустого аудиофайла: {e}")
                # вызов function
                if not text is None:
                    from function import replace_mat_in_sentence, replace_numbers_in_sentence
                    text = await replace_numbers_in_sentence(text)
                    text = await replace_mat_in_sentence(text)
                    print(text)
                    await run_main_with_settings(ctx, "робот, " + text, True)

            continue
        result = AudioSegment.from_file(wav_filename, format="wav") + AudioSegment.from_file(file_found, format="wav")
        try:
            result.export(wav_filename, format="wav")
        except Exception as e:
            print(f"Ошибка при экспорте аудио: {e}")
        print("recognize_saved")
        # удаление временного файла
        try:
            Path(file_found).unlink()
        except FileNotFoundError:
            pass
    print("Stop_Recording")


async def get_image_dimensions(file_path):
    with open(file_path, 'rb') as file:
        data = file.read(24)

    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return struct.unpack('>ii', data[16:24])
    elif data[:6] in (b'GIF87a', b'GIF89a') and data[10:12] == b'\x00\x00':
        return struct.unpack('<HH', data[6:10])
    elif data.startswith(b'\xff\xd8\xff\xe0') and data[6:10] == b'JFIF':
        return struct.unpack('>H', data[7:9])[0], struct.unpack('>H', data[9:11])[0]
    elif data.startswith(b'\xff\xd8\xff\xe1') and data[6:10] == b'Exif':
        return struct.unpack('<HH', data[10:14])[0], struct.unpack('<HH', data[14:18])[0]
    else:
        raise ValueError("Формат не поддерживается")


if __name__ == "__main__":
    print("update 1")
    arguments = sys.argv

    if len(arguments) > 1:
        discord_token = arguments[1]
    else:
        print("Укажите discord_TOKEN")
        exit(-1)
    # load models
    from GPT_runner import run
    from image_create import generate_picture

    print("load gpt model")
    pool1 = multiprocessing.Pool(processes=1)
    pool1.apply_async(run)
    pool1.close()
    print("load image model")
    pool2 = multiprocessing.Pool(processes=1)
    pool2.apply_async(generate_picture)
    pool2.close()
    print("load bot")
    bot.run(discord_token)
