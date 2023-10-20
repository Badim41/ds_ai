import datetime
import multiprocessing
import os
import random
import re
import struct
import subprocess
import configparser
import asyncio
import time

from PIL import Image
from pydub import AudioSegment

from discord import Option
from modifed_sinks import StreamSink
import speech_recognition as sr
from pathlib import Path
import sys
import discord
from discord.ext import commands
from use_free_cuda import check_cuda, use_cuda_async, stop_use_cuda_async

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
        return config.get(section, key)
    config.set(section, key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)
    return ' '.join([section, key, str(value)])


async def set_get_config(key="record", value=None):
    config.read('config.ini')
    if value is None:
        return config.get("Sound", key)
    config.set('Sound', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


async def set_get_config_default(key, value=None):
    config.read('config.ini')
    if value is None:
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


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user in message.mentions:
        text = message.content
        ctx = await bot.get_context(message)
        try:
            # получение, на какое сообщение ответили
            if message.reference:
                referenced_message = await message.channel.fetch_message(message.reference.message_id)
                reply_on_message = referenced_message.content
                if "||" in reply_on_message:
                    reply_on_message = re.sub(r'\|\|.*?\|\|', '', reply_on_message)
                text += f" (Пользователь отвечает на ваше сообщение \"{reply_on_message}\")"
            from function import replace_mat_in_sentence
            if await set_get_config_default("robot_name_need") == "False":
                text = await set_get_config_default("currentainame") + ", " + text
            text = await replace_mat_in_sentence(text)
            await set_get_config_default("user_name", value=message.author)
            await run_main_with_settings(ctx, text, True)
        except Exception as e:
            await ctx.send(f"Ошибка при команде say с параметрами {message}: {e}")
    await bot.process_commands(message)


@bot.slash_command(name="change_video",
                   description='перерисовать и переозвучить видео. Бот также предложит вам название')
async def __change_video(
        ctx,
        video_path: Option(discord.SlashCommandOptionType.attachment, description='Файл с видео',
                           required=True),
        fps: Option(int, description='Частота кадров (ОЧЕНЬ влияет на время ожидания))', required=True,
                    choices=[30, 15, 10, 6, 5, 3, 2, 1]),
        extension: Option(str, description='Расширение (сильно влияет на время ожидания)', required=True,
                          choices=["144p", "240p", "360p", "480p", "720p"]),
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
                         default=0.15, min_value=0,
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
                                         max_value=1),
        voice: Option(str, description='Голос для видео', required=False, default="None"),
        pitch: Option(str, description='Кто говорит/поёт в видео?', required=False,
                      choices=['мужчина', 'женщина'], default=None),
        indexrate: Option(float, description='Индекс голоса (от 0 до 1)', required=False, default=0.5, min_value=0,
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
                        max_value=1)
):
    try:
        # ошибки входных данных
        config.read('config.ini')
        voices = config.get("Sound", "voices").replace("\"", "").replace(",", "").split(";")
        if voice not in voices:
            return await ctx.respond("Выберите голос из списка: " + ','.join(voices))
        if await set_get_config_all("Image", "model_loaded", None) == "False":
            return await ctx.respond("модель для картинок не загружена")
        if not video_path:
            return

        # используем видеокарты
        await use_cuda_async(0)

        await ctx.defer()
        # run timer
        start_time = datetime.datetime.now()
        # save
        filename = str(random.randint(1, 1000000)) + ".mp4"
        print(filename)
        await video_path.save(filename)
        # loading params
        await set_get_config_all(f"Image", "strength_negative_prompt", strength_negative_prompt)
        await set_get_config_all(f"Image", "strength_prompt", strength_prompt)
        await set_get_config_all(f"Image", "strength", strength)
        await set_get_config_all(f"Image", "seed", seed)
        await set_get_config_all(f"Image", "steps", steps)
        await set_get_config_all(f"Image", "negative_prompt", negative_prompt)
        print("params suc")
        # wait for answer
        from video_change import video_pipeline
        video_path = await video_pipeline(filename, fps, extension, prompt, voice, pitch,
                                          indexrate, loudness, main_vocal, back_vocal, music,
                                          roomsize, wetness, dryness)
        # count time
        end_time = datetime.datetime.now()
        spent_time = str(end_time - start_time)
        # убираем миллисекунды
        spent_time = spent_time[:spent_time.find(".")]
        # отправляем
        await ctx.respond("Вот как я изменил ваше видео🖌. Потрачено " + spent_time)
        await send_file(ctx, video_path)
        # освобождаем видеокарту
        await stop_use_cuda_async(0)
    except Exception as e:
        await ctx.respond(f"Ошибка при изменении длины запроса (с параметрами\
                          {fps, extension, prompt, negative_prompt, steps, seed, strength, strength_prompt, voice, pitch, indexrate, loudness, main_vocal, back_vocal, music, roomsize, wetness, dryness}\
                          ): {e}")


@bot.slash_command(name="change_image", description='изменить изображение нейросетью')
async def __image(ctx,
                  image: Option(discord.SlashCommandOptionType.attachment, description='Изображение',
                                required=True),
                  # prompt=prompt, negative_prompt=negative_prompt, x=512, y=512, steps=50,
                  #                      seed=random.randint(1, 10000), strenght=0.5
                  prompt: Option(str, description='запрос', required=True),
                  negative_prompt: Option(str, description='негативный запрос', default="NSFW", required=False),
                  steps: Option(int, description='число шагов', required=False,
                                default=60,
                                min_value=1,
                                max_value=500),
                  seed: Option(int, description='сид изображения', required=False,
                               default=random.randint(1, 1000000),
                               min_value=1,
                               max_value=1000000),
                  x: Option(int,
                            description='изменить размер картинки по x (до 768*768)',
                            required=False,
                            default=None, min_value=64,
                            max_value=768),
                  y: Option(int,
                            description='изменить размер картинки по y (до 768*768)',
                            required=False,
                            default=None, min_value=64,
                            max_value=768),
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
    try:
        await use_cuda_async(0)
        await set_get_config_all(f"Image", "result", "None")
        await ctx.defer()
        # throw extensions
        if await set_get_config_all(f"Image", "model_loaded", None) == "False":
            return await ctx.respond("модель для картинок не загружена")
        # run timer
        start_time = datetime.datetime.now()
        input_image = "images/image" + str(random.randint(1, 1000000)) + ".png"
        await image.save(input_image)
        # get image size and round to 64
        if x is None and y is None:
            x, y = await get_image_dimensions(input_image)
            x = int(x)
            y = int(y)
        print("1X", x, "1Y", y)
        if not x % 64 == 0:
            x = ((x // 64) + 1) * 64
        if not y % 64 == 0:
            y = ((y // 64) + 1) * 64
        print("2X", x, "2Y", y)
        # во избежания ошибок из-за нехватки памяти, ограничим изображение 768x768
        while x * y > 589824:
            if x > 64:
                x -= 64
            if y > 64:
                y -= 64
        # loading params
        await set_get_config_all(f"Image", "strength_negative_prompt", strength_negative_prompt)
        await set_get_config_all(f"Image", "strength_prompt", strength_prompt)
        await set_get_config_all(f"Image", "strength", strength)
        await set_get_config_all(f"Image", "seed", seed)
        await set_get_config_all(f"Image", "steps", steps)
        await set_get_config_all(f"Image", "negative_prompt", negative_prompt)
        await set_get_config_all(f"Image", "prompt", prompt)
        await set_get_config_all(f"Image", "x", x)
        await set_get_config_all(f"Image", "y", y)
        await set_get_config_all(f"Image", "input", input_image)
        print("params suc")
        # wait for answer
        while True:
            output_image = await set_get_config_all(f"Image", "result", None)
            if not output_image == "None":
                break
            await asyncio.sleep(0.25)

        # count time
        end_time = datetime.datetime.now()
        spent_time = str(end_time - start_time)
        # убираем часы и миллисекунды
        spent_time = spent_time[spent_time.find(":") + 1:]
        spent_time = spent_time[:spent_time.find(".")]
        # отправляем
        await ctx.respond("Вот как я изменил ваше изображение🖌. Потрачено " + spent_time)
        await send_file(ctx, output_image)
        # удаляем временные файлы
        os.remove(output_image)
        # перестаём использовать видеокарту
        await stop_use_cuda_async(0)
    except Exception as e:
        await ctx.respond(f"Ошибка при изменении длины запроса (с параметрами\
                          {prompt, negative_prompt, steps, x, y, strength, strength_prompt, strength_negative_prompt}): {e}")
        # перестаём использовать видеокарту
        await stop_use_cuda_async(0)


@bot.slash_command(name="config", description='изменить конфиг (лучше не трогать, если не знаешь!)')
async def __config(
        ctx,
        section: Option(str, description='секция', required=True),
        key: Option(str, description='ключ', required=True),
        value: Option(str, description='значение', required=False, default=None)
):
    try:
        await ctx.defer()
        await ctx.respond(await set_get_config_all(section, key, value))
    except Exception as e:
        await ctx.respond(f"Ошибка при изменении конфига (с параметрами{section},{key},{value}): {e}")


@bot.slash_command(name="join", description='присоединиться к голосовому каналу')
async def join(ctx):
    try:
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
    except Exception as e:
        await ctx.respond(f"Ошибка при присоединении: {e}")


@bot.slash_command(name="record", description='воспринимать команды из микрофона')
async def record(ctx):  # if you're using commands.Bot, this will also work.
    try:
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
    except Exception as e:
        await ctx.respond(f"Ошибка при записи звука из микрофона: {e}")


@bot.slash_command(name="stop_recording", description='перестать воспринимать команды из микрофона')
async def stop_recording(ctx):
    try:
        if ctx.guild.id in connections:
            vc = connections[ctx.guild.id][0]  # Получаем элемент списка
            vc.stop_recording()
            del connections[ctx.guild.id]
        else:
            await ctx.respond("Я и так тебя не слушал ._.")
    except Exception as e:
        await ctx.respond(f"Ошибка при остановки записи микрофона: {e}")


@bot.slash_command(name="disconnect", description='выйти из войс-чата')
async def disconnect(ctx):
    try:
        await ctx.defer()
        voice = ctx.voice_client
        if voice:
            await voice.disconnect(force=True)
            await ctx.respond("выхожу")
        else:
            await ctx.respond("Я не в войсе")
        if ctx.guild.id in connections:
            del connections[ctx.guild.id]  # remove the guild from the cache.
    except Exception as e:
        await ctx.respond(f"Ошибка при выходе из войс-чата: {e}")


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
    try:
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
    except Exception as e:
        await ctx.respond(f"Ошибка при паузе: {e}")


@bot.slash_command(name="skip", description='пропуск аудио')
async def skip(ctx):
    try:
        await ctx.defer()
        await ctx.respond('Выполнение...')
        voice_client = ctx.voice_client
        if voice_client.is_playing():
            voice_client.stop()
            await ctx.respond("Текущий трек пропущен ⏭️")
            await set_get_config("stop_milliseconds", 0)
        else:
            await ctx.respond("Нет активного аудио для пропуска.")
    except Exception as e:
        await ctx.respond(f"Ошибка при пропуске: {e}")


@bot.slash_command(name="lenght", description='Длина запроса')
async def __lenght(
        ctx,
        number: Option(int, description='Длина запроса для GPT (Число от 1 до 1000)', required=True, min_value=1,
                       max_value=1000)
):
    try:
        await ctx.defer()
        await ctx.respond('Выполнение...')
        # for argument in (number,"""boolean, member, text, choice"""):
        print(f'{number} ({type(number).__name__})\n')
        await run_main_with_settings(ctx, f"робот длина запроса {number}", True)
        await ctx.respond(f"Длина запроса: {number}")
    except Exception as e:
        await ctx.respond(f"Ошибка при изменении длины запроса (с параметрами{number}): {e}")


@bot.slash_command(name="say", description='Сказать роботу что-то')
async def __say(
        ctx,
        text: Option(str, description='Сам текст/команда. Список команд: \\help-say', required=True)
):
    try:
        await ctx.respond('Выполнение...')
        from function import replace_mat_in_sentence
        if await set_get_config_default("robot_name_need") == "False":
            text = await set_get_config_default("currentainame") + ", " + text
        text = await replace_mat_in_sentence(text)
        print(f'{text} ({type(text).__name__})\n')
        await set_get_config_default("user_name", value=ctx.author.name)
        await run_main_with_settings(ctx, text, True)
    except Exception as e:
        await ctx.respond(f"Ошибка при команде say (с параметрами{text}): {e}")


@bot.slash_command(name="tts", description='_Заставить_ бота говорить всё, что захочешь')
async def __tts(
        ctx,
        text: Option(str, description='Текст для озвучки', required=True),
        ai_voice: Option(str, description='Голос для озвучки', required=False, default="None")
):
    ai_voice_temp = None
    try:
        await ctx.defer()
        await ctx.respond('Выполнение...')
        await use_cuda_async(0)
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
        # перестаём использовать видеокарту
        await stop_use_cuda_async(0)
    except Exception as e:
        await ctx.respond(f"Ошибка при озвучивании текста (с параметрами {text}): {e}")
        # возращаем голос
        if not ai_voice_temp is None:
            await set_get_config_default("currentainame", ai_voice_temp)
        # перестаём использовать видеокарту
        await stop_use_cuda_async(0)


@bot.slash_command(name="ai_cover", description='_Заставить_ бота озвучить видео/спеть песню')
async def __cover(
        ctx,
        url: Option(str, description='Ссылка на видео', required=False, default=None),
        audio_path: Option(discord.SlashCommandOptionType.attachment, description='Аудиофайл',
                           required=False, default=None),
        voice: Option(str, description='Голос для видео', required=False, default=None),
        pitch: Option(str, description='Кто говорит/поёт в видео?', required=False,
                      choices=['мужчина', 'женщина'], default=None),
        time: Option(int, description='Ограничить длительность воспроизведения (в секундах)', required=False,
                     default=-1, min_value=0),
        indexrate: Option(float, description='Индекс голоса (от 0 до 1)', required=False, default=0.5, min_value=0,
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
    param_string = None
    try:
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
        print("suc params")
        await run_main_with_settings(ctx, "робот протокол 13 " + param_string, False)
        # output..
    except Exception as e:
        await ctx.respond(f"Ошибка при изменении голоса (с параметрами {param_string}): {e}")


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
    if name == "None" or ";" in name or "/" in name or "\\" in name:
        await ctx.respond('Имя не должно содержать \";\" \"/\" \"\\\" или быть None')
    # !python download_model.py {url} {dir_name} {gender} {info}
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
            "download_model.py",
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
    print("command line:", text)
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


@bot.command(aliases=['check'], help="командная строка")
async def check_messages(ctx, *args):
    from function import chatgpt_get_result
    try:
        message = int("".join(args))
        messages = []
        async for message in ctx.channel.history(limit=message):
            messages.append(f"Сообщение от {message.author.name}: {message.content}")
        result = await chatgpt_get_result(ctx, f"Кратко перескажи о чём говорили в чате, "\
                                 f"в конце сделай небольшой свой комментарий, например: этот пользователь заслуживает наказания"\
                                 f"Вот история сообщений:{messages}")
        await ctx.send(result)
    except Exception as e:
        await ctx.send(f"Произошла ошибка: {e}")


async def run_main_with_settings(ctx, spokenText, writeAnswer):
    from function import start_bot
    await start_bot(ctx, spokenText, writeAnswer)


async def write_in_discord(ctx, text):
    print(text)
    if text == "" or text is None:
        from function import result_command_change, Color
        await result_command_change("ОТПРАВЛЕНО ПУСТОЕ СООБЩЕНИЕ", Color.RED)
        return
    if len(text) < 2000:
        await ctx.send(text)
    else:
        message_parts = []

        while len(text) > 0:
            code_block_start = text.find("```")
            spoiler_start = text.find("||")

            # первая пара
            min_start = min(code_block_start, spoiler_start) if code_block_start >= 0 and spoiler_start >= 0 else max(
                code_block_start, spoiler_start)

            if min_start == -1:
                message_parts.append(text[:2000])
                text = text[2000:]
            else:
                if text[min_start:min_start + 3] == "```":
                    code_block_end = text[min_start + 3:].find("```")
                    if code_block_end != -1:
                        message_part = text[:min_start + code_block_end + 6]
                    else:
                        message_part = text[:2000]
                else:
                    spoiler_end = text[min_start + 2:].find("||")
                    if spoiler_end != -1:
                        message_part = text[:min_start + spoiler_end + 4]
                    else:
                        message_part = text[:2000]

                message_parts.append(message_part)
                text = text[len(message_part):]

        # отправляем по частям
        for part in message_parts:
            if part == "" or part is None:
                continue
            await ctx.send(part)


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


async def max_volume(audio_file_path):
    audio = AudioSegment.from_file(audio_file_path)
    max_dBFS = audio.max_dBFS
    print(max_dBFS, type(max_dBFS))
    return max_dBFS


last_speaking = 0


async def recognize(ctx):
    global last_speaking
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
            last_speaking += 1
            # если долго не было файлов (человек перестал говорить)
            if last_speaking > float(await set_get_config("delay_record")) * 10:
                text = None
                # очищаем поток
                stream_sink.cleanup()
                last_speaking = 0
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
                    text = await set_get_config_default("currentainame") + ", " + await replace_numbers_in_sentence(
                        text)
                    text = await replace_mat_in_sentence(text)
                    print(text)
                    await set_get_config_default("user_name", value=ctx.author.name)
                    await run_main_with_settings(ctx, text, True)

            continue
        if await max_volume(file_found) > int(await set_get_config_all("Sound", "min_volume", None)):
            last_speaking = 0
        result = AudioSegment.from_file(wav_filename, format="wav") + AudioSegment.from_file(file_found, format="wav")
        try:
            result.export(wav_filename, format="wav")
        except Exception as e:
            print(f"Ошибка при экспорте аудио: {e}")
        # print("recognize_saved")
        # удаление временного файла
        try:
            Path(file_found).unlink()
        except FileNotFoundError:
            pass
    print("Stop_Recording")


async def get_image_dimensions(file_path):
    with Image.open(file_path) as img:
        sizes = img.size
    return str(sizes).replace("(", "").replace(")", "").replace(" ", "").split(",")


if __name__ == "__main__":
    print("update 2")
    try:

        # === args ===

        arguments = sys.argv

        if len(arguments) > 1:
            discord_token = arguments[1]
            # load models? (img, gpt, all)
            load_gpt = False
            load_images = False
            if len(arguments) > 2:
                args = arguments[2]
                if "gpt_local" in args:
                    load_gpt = True
                if "gpt_provider" in args:
                    asyncio.run(set_get_config_all("gpt", "use_gpt_provider", "True"))
                if "img" in args:
                    load_images = True
        else:
            # raise error & exit
            print("Укажите discord_TOKEN")
            exit(-1)
        # === load models ===
        # == load gpt ==
        if load_gpt:
            print("load gpt model")
            from GPT_runner import run

            pool = multiprocessing.Pool(processes=1)
            pool.apply_async(run)
            pool.close()

            while True:
                time.sleep(0.5)
                config.read('config.ini')
                if config.getboolean("gpt", "gpt"):
                    break

        # == load images ==
        if load_images:
            print("load image model")

            from image_create_cuda0 import generate_picture

            pool = multiprocessing.Pool(processes=1)
            pool.apply_async(generate_picture)
            pool.close()
            while True:
                time.sleep(0.5)
                config.read('config.ini')
                if config.getboolean("Image", "model_loaded"):
                    break
        # ==== load bot ====
        print("====load bot====")
        bot.run(discord_token)
    except Exception as e:
        print(f"Произошла ошибка: {e}")
