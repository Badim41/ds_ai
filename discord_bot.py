import datetime
import multiprocessing
import os
import random
import re
import subprocess
import asyncio
import time
import traceback

from pytube import Playlist

from PIL import Image
from pydub import AudioSegment
from moviepy.editor import VideoFileClip

from discord import Option
from modifed_sinks import StreamSink
import speech_recognition as sr
from pathlib import Path
import sys
import discord
from discord.ext import commands
from use_free_cuda import use_cuda_async, stop_use_cuda_async, use_cuda_images, check_cuda_images, \
    stop_use_cuda_images
from set_get_config import set_get_config_all, set_get_config_all_not_async

# Значения по умолчанию
voiceChannelErrorText = '❗ Вы должны находиться в голосовом канале ❗'

connections = {}

stream_sink = StreamSink()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='\\', intents=intents)


@bot.event
async def on_ready():
    print('Status: online')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name='AI-covers'))


@bot.event
async def on_message(message):
    # minecraft chat bot
    if message.author.id == 1165023027847757836:
        text = message.content
        ctx = await bot.get_context(message)
        from function import replace_mat_in_sentence

        if await set_get_config_all("Default", "robot_name_need") == "False":
            text = await set_get_config_all("Default", "currentainame") + ", " + text
        text = await replace_mat_in_sentence(text)
        user = text[:text.find(":")]
        if "[" in text and "]" in text:
            text = re.sub(r'[.*?]', '', text)
        await set_get_config_all("Default", "user_name", value=user)
        # info
        info_was = await set_get_config_all("Default", "currentaiinfo")
        await set_get_config_all("Default", "currentaiinfo",
                                 "Ты сейчас играешь на сервере майнкрафт GoldenFire и отвечаешь на сообщения игроков из чата")
        await run_main_with_settings(ctx, text, True)
        # info2
        await set_get_config_all("Default", "currentaiinfo", info_was)
        return

    # other users
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
            if await set_get_config_all("Default", "robot_name_need") == "False":
                text = await set_get_config_all("Default", "currentainame") + ", " + text
            text = await replace_mat_in_sentence(text)
            await set_get_config_all("Default", "user_name", value=message.author)
            await run_main_with_settings(ctx, text, True)
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(str(traceback_str))
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
    cuda_numbers = None
    try:
        # ошибки входных данных
        await ctx.defer()

        voices = (await set_get_config_all("Sound", "voices")).replace("\"", "").replace(",", "").split(";")
        if voice not in voices:
            await ctx.respond("Выберите голос из списка: " + ','.join(voices))
            return
        if await set_get_config_all(f"Image0", "model_loaded", None) == "False":
            await ctx.respond("модель для картинок не загружена")
            return
        if not video_path:
            return
        # используем видеокарты
        cuda_avaible = await check_cuda_images()
        if cuda_avaible == 0:
            await ctx.respond("Нет свободных видеокарт")
            return
        else:
            await ctx.respond(f"Используется {cuda_avaible} видеокарт для обработки видео")

        cuda_numbers = []
        for i in range(cuda_avaible):
            cuda_numbers.append(await use_cuda_images())

        # run timer
        start_time = datetime.datetime.now()
        # save
        filename = str(random.randint(1, 1000000)) + ".mp4"
        print(filename)
        await video_path.save(filename)
        # сколько кадров будет в результате
        video_clip = VideoFileClip(filename)
        total_frames = int((video_clip.fps * video_clip.duration) / (30 / fps))
        max_frames = int(await set_get_config_all("Video", "max_frames", None))
        if max_frames <= total_frames:
            await ctx.send(
                f"Слишком много кадров, снизьте параметр FPS! Максимальное разрешённое количество кадров в видео: {max_frames}. Количество кадров у вас - {total_frames}")
            for i in cuda_numbers:
                await stop_use_cuda_async(i)
            return
        else:
            # на kaggle тратится около 13 секунд, на колаб - 16
            if len(cuda_numbers) > 1:
                seconds = total_frames * 13 / len(cuda_numbers)
            else:
                seconds = total_frames * 16
            if seconds >= 3600:
                hours = seconds // 3600
                minutes = (seconds % 3600) // 60
                remaining_seconds = seconds % 60
                if minutes == 0 and remaining_seconds == 0:
                    time_spend = f"{hours} часов"
                elif remaining_seconds == 0:
                    time_spend = f"{hours} часов, {minutes} минут"
                elif minutes == 0:
                    time_spend = f"{hours} часов, {remaining_seconds} секунд"
                else:
                    time_spend = f"{hours} часов, {minutes} минут, {remaining_seconds} секунд"
            elif seconds >= 60:
                minutes = seconds // 60
                remaining_seconds = seconds % 60
                if remaining_seconds == 0:
                    time_spend = f"{minutes} минут"
                else:
                    time_spend = f"{minutes} минут, {remaining_seconds} секунд"
            else:
                time_spend = f"{seconds} секунд"
            await ctx.send(f"Видео будет обрабатываться ~{time_spend}")
        # loading params
        for i in cuda_numbers:
            await set_get_config_all(f"Image{i}", "strength_negative_prompt", strength_negative_prompt)
            await set_get_config_all(f"Image{i}", "strength_prompt", strength_prompt)
            await set_get_config_all(f"Image{i}", "strength", strength)
            await set_get_config_all(f"Image{i}", "seed", seed)
            await set_get_config_all(f"Image{i}", "steps", steps)
            await set_get_config_all(f"Image{i}", "negative_prompt", negative_prompt)
        print("params suc")
        # wait for answer
        from video_change import video_pipeline
        video_path = await video_pipeline(filename, fps, extension, prompt, voice, pitch,
                                          indexrate, loudness, main_vocal, back_vocal, music,
                                          roomsize, wetness, dryness, cuda_numbers)
        # count time
        end_time = datetime.datetime.now()
        spent_time = str(end_time - start_time)
        # убираем миллисекунды
        spent_time = spent_time[:spent_time.find(".")]
        # отправляем
        await ctx.send("Вот как я изменил ваше видео🖌. Потрачено " + spent_time)
        await send_file(ctx, video_path)
        # освобождаем видеокарты
        for i in cuda_numbers:
            await stop_use_cuda_images(i)
    except Exception as e:
        await ctx.send(f"Ошибка при изменении картинки (с параметрами\
                          {fps, extension, prompt, negative_prompt, steps, seed, strength, strength_prompt, voice, pitch, indexrate, loudness, main_vocal, back_vocal, music, roomsize, wetness, dryness}\
                          ): {e}")
        if cuda_numbers:
            for i in range(cuda_avaible):
                await stop_use_cuda_images(i)
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        raise e


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
                               default=None,
                               min_value=1,
                               max_value=9007199254740991),
                  x: Option(int,
                            description='изменить размер картинки по x',
                            required=False,
                            default=None, min_value=64,
                            max_value=768),
                  y: Option(int,
                            description='изменить размер картинки по y',
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
                                                   max_value=1),
                  repeats: Option(int,
                                  description='Количество повторов',
                                  required=False,
                                  default=1, min_value=1,
                                  max_value=16)
                  ):
    await ctx.defer()
    for i in range(repeats):
        cuda_number = None
        try:
            try:
                cuda_number = await use_cuda_images()
            except Exception:
                await ctx.respond("Нет свободных видеокарт")
                return

            await set_get_config_all(f"Image{cuda_number}", "result", "None")
            # throw extensions
            if await set_get_config_all(f"Image{cuda_number}", "model_loaded", None) == "False":
                return await ctx.respond("модель для картинок не загружена")
            # run timer
            start_time = datetime.datetime.now()
            input_image = "images/image" + str(random.randint(1, 1000000)) + ".png"
            await image.save(input_image)
            # get image size and round to 64
            if x is None or y is None:
                x, y = await get_image_dimensions(input_image)
                x = int(x)
                y = int(y)
            # скэйлинг во избежания ошибок из-за нехватки памяти
            scale_factor = (1000000 / (x * y)) ** 0.5
            x = int(x * scale_factor)
            y = int(y * scale_factor)
            if not x % 64 == 0:
                x = ((x // 64) + 1) * 64
            if not y % 64 == 0:
                y = ((y // 64) + 1) * 64
            print("X:", x, "Y:", y)
            # loading params
            if seed is None:
                seed = random.randint(1, 9007199254740991)
            await set_get_config_all(f"Image{cuda_number}", "strength_negative_prompt", strength_negative_prompt)
            await set_get_config_all(f"Image{cuda_number}", "strength_prompt", strength_prompt)
            await set_get_config_all(f"Image{cuda_number}", "strength", strength)
            await set_get_config_all(f"Image{cuda_number}", "seed", seed)
            await set_get_config_all(f"Image{cuda_number}", "steps", steps)
            await set_get_config_all(f"Image{cuda_number}", "negative_prompt", negative_prompt)
            await set_get_config_all(f"Image{cuda_number}", "prompt", prompt)
            await set_get_config_all(f"Image{cuda_number}", "x", x)
            await set_get_config_all(f"Image{cuda_number}", "y", y)
            await set_get_config_all(f"Image{cuda_number}", "input", input_image)
            print("params suc")
            # wait for answer
            while True:
                output_image = await set_get_config_all(f"Image{cuda_number}", "result", None)
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
            if repeats == 1:
                await ctx.respond("Вот как я изменил ваше изображение🖌. Потрачено " + spent_time)
            else:
                await ctx.send("Вот как я изменил ваше изображение🖌. Потрачено " + spent_time)
            await send_file(ctx, output_image, delete_file=True)
            # перестаём использовать видеокарту
            await stop_use_cuda_images(cuda_number)
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(str(traceback_str))
            await ctx.send(f"Ошибка при изменении картинки (с параметрами\
                              {prompt, negative_prompt, steps, x, y, strength, strength_prompt, strength_negative_prompt}): {e}")
            # перестаём использовать видеокарту
            if not cuda_number is None:
                await stop_use_cuda_images(cuda_number)


@bot.slash_command(name="config", description='изменить конфиг (лучше не трогать, если не знаешь!)')
async def __config(
        ctx,
        section: Option(str, description='секция', required=True),
        key: Option(str, description='ключ', required=True),
        value: Option(str, description='значение', required=False, default=None)
):
    try:
        await ctx.defer()
        result = await set_get_config_all(section, key, value)
        if value is None:
            await ctx.respond(result)
        else:
            await ctx.respond(section + " " + key + " " + value)
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Ошибка при изменении конфига (с параметрами{section},{key},{value}): {e}")


@bot.slash_command(name="read_messages", description='Читает последние x сообщений из чата и делает по ним вывод')
async def __read_messages(
        ctx,
        number: Option(int, description='количество сообщений (от 1 до 100', required=True, min_value=1,
                       max_value=100),
        prompt: Option(str, description='Промпт для GPT. Какой вывод сделать по сообщениям (перевести, пересказать)',
                       required=True)
):
    await ctx.defer()
    from function import chatgpt_get_result, text_to_speech
    try:
        messages = []
        async for message in ctx.channel.history(limit=number):
            messages.append(f"Сообщение от {message.author.name}: {message.content}")
        # От начала до конца
        messages = messages[::-1]
        # убираем последнее / последние сообщения
        messages = messages[:number - 1]
        print(messages)
        result = await chatgpt_get_result(f"{prompt}. Вот история сообщений:{messages}", ctx)
        print(result)
        await ctx.respond(result)
        await text_to_speech(result, False, ctx)
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Произошла ошибка: {e}")


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
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
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
        await set_get_config_all("Sound", "record", "True")
        await ctx.respond("Внимательно вас слушаю")
        await recognize(ctx)
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Ошибка при записи звука из микрофона: {e}")


@bot.slash_command(name="stop_recording", description='перестать воспринимать команды из микрофона')
async def stop_recording(ctx):
    try:
        if ctx.guild.id in connections:
            vc = connections[ctx.guild.id][0]  # Получаем элемент списка
            vc.stop_recording()
            del connections[ctx.guild.id]
            await ctx.respond("Я перестал вас слышать")
        else:
            await ctx.respond("Я и так тебя не слушал ._.")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
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
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
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


@bot.slash_command(name="pause", description='пауза/воспроизведение (остановка диалога)')
async def pause(ctx):
    try:
        await ctx.defer()
        if await set_get_config_all("dialog", "dialog", None) == "True":
            await set_get_config_all("dialog", "dialog", "False")
            await ctx.respond("Диалог остановлен")

            # скипаем аудио
            voice_client = ctx.voice_client
            if voice_client.is_playing():
                voice_client.stop()
                await set_get_config_all("Sound", "stop_milliseconds", 0)
                await set_get_config_all("Sound", "playing", "False")
            return
        voice_client = ctx.voice_client
        if voice_client.is_playing():
            # voice_client.pause()
            await set_get_config_all("Sound", "pause", "True")
            await ctx.respond("Пауза ⏸")
        elif voice_client.is_paused():
            # voice_client.resume()
            await set_get_config_all("Sound", "pause", "False")
            await ctx.respond("Продолжаем воспроизведение ▶️")
        else:
            await ctx.respond("Нет активного аудио для приостановки или продолжения.")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Ошибка при паузе: {e}")


@bot.slash_command(name="skip", description='пропуск аудио')
async def skip(ctx):
    try:
        await ctx.defer()
        await ctx.respond('Выполнение...')
        voice_client = ctx.voice_client
        if voice_client.is_playing():
            voice_client.stop()
            await ctx.respond("Аудио пропущено ⏭️")
            await set_get_config_all("Sound", "stop_milliseconds", 0)
            await set_get_config_all("Sound", "playing", "False")
        else:
            await ctx.respond("Нет активного аудио для пропуска.")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
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
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Ошибка при изменении длины запроса (с параметрами{number}): {e}")


@bot.slash_command(name="say", description='Сказать роботу что-то')
async def __say(
        ctx,
        text: Option(str, description='Сам текст/команда. Список команд: \\help-say', required=True),
        gpt_mode: Option(str, description="модификация GPT. 'all' - все ответы, 'fast' - быстрый, 'None' - точный",
                         choices=["fast", "all", "None"], required=False, default=None)
):
    try:
        await ctx.respond('Выполнение...')

        if gpt_mode:
            await set_get_config_all("gpt", "gpt_mode", gpt_mode)

        from function import replace_mat_in_sentence
        if await set_get_config_all("Default", "robot_name_need") == "False":
            text = await set_get_config_all("Default", "currentainame") + ", " + text
        text = await replace_mat_in_sentence(text)
        print(f'{text} ({type(text).__name__})\n')
        await set_get_config_all("Default", "user_name", value=ctx.author.name)

        await run_main_with_settings(ctx, text, True)
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Ошибка при команде say (с параметрами{text}): {e}")


@bot.slash_command(name="tts", description='_Заставить_ бота говорить всё, что захочешь')
async def __tts(
        ctx,
        text: Option(str, description='Текст для озвучки', required=True),
        ai_voice: Option(str, description='Голос для озвучки', required=False, default=None),
        output: Option(bool, description='Отправить результат', required=False, default=False)
):
    ai_voice_temp = None
    try:
        await ctx.defer()
        await ctx.respond('Выполнение...')
        # count time
        start_time = datetime.datetime.now()
        await use_cuda_async(0)
        voices = (await set_get_config_all("Sound", "voices")).replace("\"", "").replace(",", "").split(";")
        if str(ai_voice) not in voices:
            return await ctx.respond("Выберите голос из списка: " + ','.join(voices))
        from function import replace_mat_in_sentence, mat_found
        text = await replace_mat_in_sentence(text)
        if mat_found:
            await ctx.respond("Такое нельзя произносить!")
            return
        print(f'{text} ({type(text).__name__})\n')
        # меняем голос
        voices = (await set_get_config_all("Sound", "voices")).replace("\"", "").replace(",", "").split(";")
        ai_voice_temp = await set_get_config_all("Default", "currentainame")
        if ai_voice is None:
            ai_voice = await set_get_config_all("Default", "currentainame")
            print(await set_get_config_all("Default", "currentainame"))
        elif ai_voice not in voices:
            return await ctx.respond("Выберите голос из списка: " + ','.join(voices))
        await set_get_config_all("Default", "currentainame", ai_voice)
        # запускаем TTS
        from function import text_to_speech
        await text_to_speech(text, False, ctx, ai_dictionary=ai_voice)
        # await run_main_with_settings(ctx, f"робот протокол 24 {text}",
        #                              False)  # await text_to_speech(text, False, ctx, ai_dictionary=ai_voice)
        # перестаём использовать видеокарту
        await stop_use_cuda_async(0)

        # count time
        end_time = datetime.datetime.now()
        spent_time = str(end_time - start_time)
        # убираем миллисекунды
        spent_time = spent_time[:spent_time.find(".")]
        if "0:00:00" not in str(spent_time):
            await ctx.respond("Потрачено на обработку:" + spent_time)
        if output:
            await send_file(ctx, "2.mp3")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Ошибка при озвучивании текста (с параметрами {text}): {e}")
        # возращаем голос
        if not ai_voice_temp is None:
            await set_get_config_all("Default", "currentainame", ai_voice_temp)
        # перестаём использовать видеокарту
        await stop_use_cuda_async(0)


async def get_links_from_playlist(playlist_url):
    try:
        playlist = Playlist(playlist_url)
        playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
        video_links = playlist.video_urls
        video_links = str(video_links).replace("'", "").replace("[", "").replace("]", "").replace(" ", "").replace(",",
                                                                                                                   ";")
        return video_links
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        print(f"Произошла ошибка при извлечении плейлиста: {e}")
        return []


@bot.slash_command(name="ai_cover", description='_Заставить_ бота озвучить видео/спеть песню')
async def __cover(
        ctx,
        url: Option(str, description='Ссылка на видео', required=False, default=None),
        audio_path: Option(discord.SlashCommandOptionType.attachment, description='Аудиофайл',
                           required=False, default=None),
        voice: Option(str, description='Голос для видео', required=False, default=None),
        gender: Option(str, description='Кто говорит/поёт в видео? (или указать pitch)', required=False,
                       choices=['мужчина', 'женщина'], default=None),
        pitch: Option(int, description='Какую использовать тональность (от -24 до 24) (или указать gender)',
                      required=False,
                      default=0, min_value=-24, max_value=24),
        time: Option(int, description='Ограничить длительность воспроизведения (в секундах)', required=False,
                     default=-1, min_value=-1),
        indexrate: Option(float, description='Индекс голоса (от 0 до 1)', required=False, default=0.5, min_value=0,
                          max_value=1),
        loudness: Option(float, description='Громкость шума (от 0 до 1)', required=False, default=0.4, min_value=0,
                         max_value=1),
        filter_radius: Option(int,
                              description='Насколько далеко от каждой точки в данных будут учитываться значения... (от 1 до 7)',
                              required=False, default=3, min_value=0,
                              max_value=7),
        main_vocal: Option(int, description='Громкость основного вокала (от -20 до 0)', required=False, default=0,
                           min_value=-20, max_value=0),
        back_vocal: Option(int, description='Громкость бэквокала (от -20 до 0)', required=False, default=0,
                           min_value=-20, max_value=0),
        music: Option(int, description='Громкость музыки (от -20 до 0)', required=False, default=0, min_value=-20,
                      max_value=0),
        roomsize: Option(float, description='Размер помещения (от 0 до 1)', required=False, default=0.2, min_value=0,
                         max_value=1),
        wetness: Option(float, description='Влажность (от 0 до 1)', required=False, default=0.2, min_value=0,
                        max_value=1),
        dryness: Option(float, description='Сухость (от 0 до 1)', required=False, default=0.8, min_value=0,
                        max_value=1),
        palgo: Option(str, description='Алгоритм. Rmvpe - лучший вариант, mangio-crepe - более мягкий вокал',
                      required=False,
                      choices=['rmvpe', 'mangio-crepe'], default="rmvpe"),
        hop: Option(int, description='Как часто проверяет изменения тона в mango-crepe', required=False, default=128,
                    min_value=64,
                    max_value=1280),
        start: Option(int, description='Начать воспроизводить с (в секундах). -1 для продолжения', required=False,
                      default=0, min_value=-2),
        output: Option(str, description='Отправить результат', choices=["link", "file", "all_files", "None"],
                       required=False, default="file"),
        only_voice_change: Option(bool,
                                  description='Не извлекать инструментал и бэквокал, изменить голос. Не поддерживаются ссылки',
                                  required=False, default=False)
):
    param_string = None
    try:
        await ctx.defer()
        await ctx.respond('Выполнение...')
        params = []
        if voice is None:
            voice = await set_get_config_all("Default", "currentAIname")
        if voice:
            params.append(f"-voice {voice}")
        # если мужчина-мужчина, женщина-женщина, pitch не меняем
        pitch_int = pitch
        # если женщина, а AI мужчина = -12,
        if gender == 'женщина':
            if await set_get_config_all("Default", "currentaipitch") == "0":
                pitch_int = -12
        # если мужчина, а AI женщина = 12,
        elif gender == 'мужчина':
            if not await set_get_config_all("Default", "currentaipitch") == "0":
                pitch_int = 12
        params.append(f"-pitch {pitch_int}")
        if time is None:
            params.append(f"-time -1")
        else:
            params.append(f"-time {time}")
        if palgo != "rmvpe":
            params.append(f"-palgo {palgo}")
        if hop != 128:
            params.append(f"-hop {hop}")
        if indexrate != 0.5:
            params.append(f"-indexrate {indexrate}")
        if loudness != 0.2:
            params.append(f"-loudness {loudness}")
        if filter_radius != 3:
            params.append(f"-filter_radius {filter_radius}")
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
        if start == -2:
            stop_seconds = int(await set_get_config_all("Sound", "stop_milliseconds", None)) // 1000
            params.append(f"-start {stop_seconds}")
        elif start == -1 or start != 0:
            params.append(f"-start {start}")
        if output != "None":
            params.append(f"-output {output}")

        param_string = ' '.join(params)
        print("suc params")
        # time start
        start_time = datetime.datetime.now()
        if audio_path:
            filename = str(random.randint(1, 1000000)) + ".mp3"
            await audio_path.save(filename)
            # Изменить ТОЛЬКО ГОЛОС
            if only_voice_change:
                try:
                    command = [
                        "python",
                        "only_voice_change_cuda0.py",
                        "-i", f"{filename}",
                        "-o", f"{filename}",
                        "-dir", str(voice),
                        "-p", f"{pitch_int}",
                        "-ir", f"{indexrate}",
                        "-fr", f"{filter_radius}",
                        "-rms", f"{roomsize}",
                        "-pro", "0.05"
                    ]
                    print("run RVC, AIName:", voice)
                    subprocess.run(command, check=True)
                    await send_file(ctx, filename, delete_file=True)
                except subprocess.CalledProcessError as e:
                    traceback_str = traceback.format_exc()
                    print(str(traceback_str))
                    await ctx.respond(f"Ошибка при изменении голоса(ID:d1): {e}")
            else:
                # изменить голос без музыки
                param_string += f" -url {filename} "
                await run_main_with_settings(ctx, "робот протокол 13 " + param_string, False)
        elif url:
            if ";" in url:
                urls = url.split(";")
            elif "playlist" in url:
                urls = await get_links_from_playlist(url)
                urls = urls.split(";")
                if urls == "" or urls is None:
                    ctx.respond("Ошибка нахождения видео в плейлисте")
            else:
                urls = [url]
            args = ""
            i = 0
            for one_url in urls:
                i += 1
                args += f"робот протокол 13 -url {one_url} {param_string}\n"
            await run_main_with_settings(ctx, args, True)
        else:
            await ctx.respond('Не указана ссылка или аудиофайл')
            return
        end_time = datetime.datetime.now()
        spent_time = str(end_time - start_time)
        # убираем миллисекунды
        spent_time = spent_time[:spent_time.find(".")]
        if not "0:00:00" in str(spent_time):
            await ctx.respond("Потрачено на обработку:" + spent_time)
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Ошибка при изменении голоса(ID:d5) (с параметрами {param_string}): {e}")


@bot.slash_command(name="create_dialog", description='Имитировать диалог людей')
async def __dialog(
        ctx,
        names: Option(str, description="Участники диалога через ';' (у каждого должен быть добавлен голос!)",
                      required=True),
        theme: Option(str, description="Начальная тема разговора", required=False, default="случайная тема"),
        prompt: Option(str, description="Общий запрос для всех диалогов", required=False, default="")
):
    try:
        await ctx.defer()
        await ctx.respond('Выполнение...')
        if await set_get_config_all("dialog", "dialog", None) == "True":
            await ctx.respond("Уже идёт диалог!")
            return
        # отчищаем прошлые диалоги
        with open("caversAI/dialog_create.txt", "w"):
            pass
        with open("caversAI/dialog_play.txt", "w"):
            pass
        voices = (await set_get_config_all("Sound", "voices")).replace("\"", "").replace(",", "").split(";")
        voices.remove("None")  # убираем, чтобы не путаться
        names = names.split(";")
        if len(names) < 2:
            await ctx.respond("Должно быть как минимум 2 персонажа")
            return
        infos = []
        for name in names:
            if name not in voices:
                await ctx.respond("Выберите голоса из списка: " + ','.join(voices))
                return
            with open(f"rvc_models/{name}/info.txt") as reader:
                file_content = reader.read().replace("Вот информация о тебе:", "")
                infos.append(f"Вот информация о {name}: {file_content}")
        await set_get_config_all("dialog", "dialog", "True")
        await set_get_config_all("gpt", "gpt_mode", "None")
        # names, theme, infos, prompt, ctx
        # запустим сразу 8 процессов для обработки голоса
        await asyncio.gather(gpt_dialog(names, theme, infos, prompt, ctx), play_dialog(ctx),
                             create_audio_dialog(ctx, 0, "dialog"), create_audio_dialog(ctx, 1, "dialog"),
                             create_audio_dialog(ctx, 2, "dialog"), create_audio_dialog(ctx, 3, "dialog"),
                             create_audio_dialog(ctx, 4, "dialog"), create_audio_dialog(ctx, 5, "dialog"),
                             create_audio_dialog(ctx, 6, "dialog"), create_audio_dialog(ctx, 7, "dialog"))
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Ошибка при диалоге: {e}")


@bot.slash_command(name="add_voice", description='Добавить RVC голос')
async def __add_voice(
        ctx,
        url: Option(str, description='Ссылка на .zip файл с моделью RVC', required=True),
        name: Option(str, description=f'Имя модели', required=True),
        gender: Option(str, description=f'Пол (для настройки тональности)', required=True,
                       choices=['мужчина', 'женщина']),
        info: Option(str, description=f'Какие-то сведения о данном человеке', required=False,
                     default="Отсутствует"),
        speed: Option(float, description=f'Ускорение/замедление голоса', required=False,
                      default=1, min_value=0.5, max_value=2),
        change_voice: Option(bool, description=f'(необязательно) Изменить голос на этот', required=False,
                             default=False)
):
    await ctx.defer()
    await ctx.respond('Выполнение...')
    if name == "None" or ";" in name or "/" in name or "\\" in name:
        await ctx.respond('Имя не должно содержать \";\" \"/\" \"\\\" или быть None')
    # !python download_voice_model.py {url} {dir_name} {gender} {info}
    name = name.replace(" ", "_")
    if gender == "женщина":
        gender = "female"
    elif gender == "мужчина":
        gender = "male"
    else:
        gender = "male"
    try:
        command = [
            "python",
            "download_voice_model.py",
            url,
            name,
            gender,
            f"{info}",
            str(speed)
        ]
        subprocess.run(command, check=True)
        voices = (await set_get_config_all("Sound", "voices")).split(";")
        voices.append(name)
        await set_get_config_all("Sound", "voices", ';'.join(voices))
        if change_voice:
            await run_main_with_settings(ctx, f"робот измени голос на {name}", True)
        await ctx.send(f"Модель {name} успешно установлена!")
    except subprocess.CalledProcessError as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.respond(f"Голос уже существует, но параметры были изменены")


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
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.send(f"Ошибка выполнения команды: {e}")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.send(f"Произошла неизвестная ошибка: {e}")


async def play_dialog(ctx):
    number = int(await set_get_config_all("dialog", "play_number", None))
    while await set_get_config_all("dialog", "dialog", None) == "True":
        try:
            files = os.listdir("song_output")
            files = sorted(files)
            for file in files:
                if file.startswith(str(number)):
                    with open("caversAI/dialog_play.txt", "r") as reader:
                        lines = reader.read()
                        if file not in lines:
                            await asyncio.sleep(0.1)
                            continue
                    from function import playSoundFile
                    number += 1
                    await set_get_config_all("dialog", "play_number", number)
                    speaker = file[:file.find(".")]
                    speaker = re.sub(r'\d', '', speaker)
                    await ctx.send("говорит " + speaker)
                    await playSoundFile("song_output/" + file, -1, 0, ctx)
                    os.remove("song_output/" + file)
                    await ctx.send("end")
                else:
                    await asyncio.sleep(0.2)
        except Exception as e:
            traceback_str = traceback.format_exc()
            print(str(traceback_str))
            await ctx.send(f"Ошибка при изменении голоса(ID:d2): {e}")


async def text_to_speech_file(tts, currentpitch, file_name):
    from elevenlabs import generate, save, set_api_key
    language = await set_get_config_all("Default", "language", None)
    max_simbols = await set_get_config_all("voice", "max_simbols", None)

    pitch = 0
    if len(tts) > int(max_simbols) or await set_get_config_all("voice", "avaible_tokens", None) == "None":
        print("gtts1")
        from function import gtts
        await gtts(tts, language[:2], file_name)
        if currentpitch == 0:
            pitch = -12
    else:
        # получаем ключ для elevenlab
        keys = (await set_get_config_all("voice", "avaible_tokens", None)).split(";")
        key = keys[0]
        if not key == "Free":
            set_api_key(key)
        try:
            # голос TTS в зависимости от пола
            if currentpitch == 0:
                voice = "Arnold"
            else:
                voice = "Bella"
            audio = generate(
                text=tts,
                model='eleven_multilingual_v2',
                voice=voice
            )

            save(audio, file_name)
        except Exception as e:
            from function import remove_unavaible_voice_token
            print(f"Ошибка при выполнении команды (ID:f16): {e}")
            traceback_str = traceback.format_exc()
            print(str(traceback_str))
            await remove_unavaible_voice_token()
            pitch = await text_to_speech_file(tts, currentpitch, file_name)
            return pitch
            # gtts(tts, language[:2], file_name)
    return pitch


async def create_audio_dialog(ctx, cuda, wait_untill):
    await asyncio.sleep(cuda * 0.11 + 0.05)
    cuda = cuda % 2

    while True:
        text_path = "caversAI/dialog_create.txt"
        play_path = "caversAI/dialog_play.txt"
        with open(text_path, "r") as reader:
            line = reader.readline()
            if not line is None and not line.replace(" ", "") == "":
                await remove_line_from_txt(text_path, 1)
                name = line[line.find("-voice") + 7:].replace("\n", "")
                with open(os.path.join(f"rvc_models/{name}/gender.txt"), "r") as file:
                    pitch = 0
                    if file.read().lower() == "female":
                        pitch = 12
                filename = int(await set_get_config_all("dialog", "files_number", None))
                await set_get_config_all("dialog", "files_number", filename + 1)
                filename = "song_output/" + str(filename) + name + ".mp3"
                pitch = await text_to_speech_file(line[:line.find("-voice")], pitch, filename)
                try:
                    command = [
                        "python",
                        f"only_voice_change_cuda{cuda}.py",
                        "-i", f"{filename}",
                        "-o", f"{filename}",
                        "-dir", name,
                        "-p", f"{pitch}",
                        "-ir", "0.5",
                        "-fr", "3",
                        "-rms", "0.3",
                        "-pro", "0.15",
                        "-slow"  # значение для диалога
                    ]
                    print("run RVC, AIName:", name)
                    from function import execute_command
                    await execute_command(' '.join(command), ctx)

                    # диалог завершён.
                    print("DIALOG_TEMP:", await set_get_config_all("dialog", wait_untill, None))
                    if await set_get_config_all("dialog", wait_untill, None) == "False":
                        return

                    # применение ускорения
                    if await set_get_config_all("Sound", "change_speed", None) == "True":
                        with open(os.path.join(f"rvc_models/{name}/speed.txt"), "r") as reader:
                            speed = float(reader.read())
                            # print("SPEED:", speed)
                        from function import speed_up_audio
                        await speed_up_audio(filename, speed)
                    with open(play_path, "a") as writer:
                        writer.write(filename + "\n")
                except Exception as e:
                    traceback_str = traceback.format_exc()
                    print(str(traceback_str))
                    await ctx.send(f"Ошибка при изменении голоса(ID:d3): {e}")
            else:
                await asyncio.sleep(0.5)


async def remove_line_from_txt(file_path, delete_line):
    try:
        if not os.path.exists(file_path):
            return
        lines = []
        with open(file_path, "r") as reader:
            i = 1
            for line in reader:
                if not i == delete_line:
                    lines.append(line)
                i += 1
        with open(file_path, "w") as writer:
            for line in lines:
                writer.write(line)
    except Exception as e:
        raise f"Ошибка при удалении строки: {e}"


async def gpt_dialog(names, theme, infos, prompt_global, ctx):
    from function import chatgpt_get_result
    # Делаем диалог между собой
    if await set_get_config_all("dialog", "dialog", None) == "True":
        prompt = (f"Привет, chatGPT. Вы собираетесь сделать диалог между {', '.join(names)}. На тему \"{theme}\". "
                  f"персонажи должны соответствовать своему образу насколько это возможно. "
                  f"{'.'.join(infos)}. {prompt_global}. "
                  f"Обязательно в конце диалога напиши очень кратко что произошло в этом диалоги и что должно произойти дальше. "
                  f"Выведи диалог в таком формате:[Говорящий]: [текст, который он произносит]")
        result = (await chatgpt_get_result(prompt, ctx)).replace("[", "").replace("]", "")
        # await write_in_discord(ctx, result)
        with open("caversAI/dialog_create.txt", "a") as writer:
            for line in result.split("\n"):
                for name in names:
                    # Человек: привет
                    # Человек (man): привет
                    if line.startswith(name):
                        line = line[line.find(":") + 1:]
                        writer.write(line + f"-voice {name}\n")

        while await set_get_config_all("dialog", "dialog", None) == "True":
            try:
                if "\n" in result:
                    result = result[result.rfind("\n"):]
                spoken_text = ""
                spoken_text_config = await set_get_config_all("dialog", "user_spoken_text", None)
                if not spoken_text_config == "None":
                    spoken_text = "Отвечайт зрителям! Зрители за прошлый диалог написали:\"" + spoken_text_config + "\""
                    await set_get_config_all("dialog", "user_spoken_text", "None")
                random_int = random.randint(1, 33)
                if not random_int == 0:
                    prompt = (f"Привет chatGPT, продолжи диалог между {', '.join(names)}. "
                              f"{'.'.join(infos)}. {prompt_global} "
                              f"персонажи должны соответствовать своему образу насколько это возможно. "
                              f"Никогда не пиши приветствие в начале этого диалога. "
                              f"Никогда не повторяй то, что было в прошлом диалоге! Вот что было в прошлом диалоге:\"{result}\". {spoken_text}"
                              f"\nОбязательно в конце напиши очень кратко что произошло в этом диалоги и что должно произойти дальше. "
                              f"Выведи диалог в таком формате:[Говорящий]: [текст, который он произносит]")
                else:
                    prompt = (
                        f"Привет, chatGPT. Вы собираетесь сделать диалог между {', '.join(names)} на случайную тему,"
                        f" которая должна относиться к событиям сервера. "
                        f"Персонажи должны соответствовать своему образу насколько это возможно. "
                        f"Никогда не пиши приветствие в начале этого диалога. "
                        f"{'.'.join(infos)}. {prompt_global}. {spoken_text}"
                        f"Обязательно в конце напиши очень кратко что произошло в этом диалоги и что должно произойти дальше. "
                        f"Выведи диалог в таком формате:[Говорящий]: [текст, который он произносит]")
                print("PROMPT:", prompt)
                result = (await chatgpt_get_result(prompt, ctx)).replace("[", "").replace("]", "")
                # await write_in_discord(ctx, result)
                with open("caversAI/dialog_create.txt", "a") as writer:
                    for line in result.split("\n"):
                        for name in names:
                            # Человек: привет
                            # Человек (man): привет
                            if line.startswith(name):
                                line = line[line.find(":") + 1:]
                                writer.write(line + f"-voice {name}\n")
                                break
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(str(traceback_str))
                await ctx.send(f"Ошибка при изменении голоса(ID:d4): {e}")


async def run_main_with_settings(ctx, spokenText, writeAnswer):
    from function import start_bot
    await start_bot(ctx, spokenText, writeAnswer)


async def write_in_discord(ctx, text):
    from function import result_command_change, Color
    if text == "" or text is None:
        await result_command_change("ОТПРАВЛЕНО ПУСТОЕ СООБЩЕНИЕ", Color.RED)
        return
    if len(text) < 1990:
        await ctx.send(text)
    else:
        # начинает строку с "```" если оно встретилось и убирает, когда "```" опять появится
        add_format = False
        lines = text.split("\n")
        for line in lines:
            if "```" in line:
                add_format = not add_format
            if line.strip():
                if add_format:
                    line = line.replace("```", "")
                    line = "```" + line + "```"
                await ctx.send(line)


async def send_file(ctx, file_path, delete_file=False):
    try:
        await ctx.send(file=discord.File(file_path))
        if delete_file:
            await asyncio.sleep(3)
            os.remove(file_path)
    except FileNotFoundError:
        await ctx.send('Файл не найден.')
    except discord.HTTPException as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        await ctx.send(f'Произошла ошибка при отправке файла: {e}.')


async def playSoundFileDiscord(ctx, audio_file_path, duration, start_seconds):
    # Проверяем, находится ли бот в голосовом канале
    if start_seconds == -1:
        start_seconds = int(await set_get_config_all("Sound", "stop_milliseconds", None)) // 1000
    try:
        if not ctx.voice_client:
            await ctx.send("Бот не находится в голосовом канале. Используйте команду `join`, чтобы присоединить его.")
            return
        # Проверяем, играет ли что-то уже
        while await set_get_config_all("Sound", "playing", None) == "True":
            await asyncio.sleep(0.1)
        await set_get_config_all("Sound", "playing", "True")
        # проигрываем
        source = discord.FFmpegPCMAudio(audio_file_path, options=f"-ss {start_seconds} -t {duration}")
        ctx.voice_client.play(source)

        # Ожидаем окончания проигрывания
        resume = False
        while ctx.voice_client.is_playing():

            await asyncio.sleep(1)
            voice_client = ctx.voice_client
            pause = await set_get_config_all("Sound", "pause", None) == "True"
            if pause:
                resume = True
                voice_client.pause()
                while await set_get_config_all("Sound", "pause", None) == "True":
                    await asyncio.sleep(0.25)
            if resume:
                voice_client.resume()

            # stop_milliseconds += 1000
            await set_get_config_all("Sound", "stop_milliseconds",
                                     int(await set_get_config_all("Sound", "stop_milliseconds")) + 1000)
        await set_get_config_all("Sound", "playing", "False")
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        print(f"Ошибка, {e}")
        await set_get_config_all("Sound", "playing", "False")


async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    await set_get_config_all("Sound", "record", "False")
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
        if await set_get_config_all("Sound", "record") == "False":
            print("Stopped listening2.")
            return
        file_found = []
        # проверяем наличие временных файлов
        for filename in os.listdir(os.getcwd()):
            if filename.startswith("output") and filename.endswith(".wav"):
                file_found.append(filename)
                break
        if len(file_found) == 0:
            await asyncio.sleep(0.1)
            last_speaking += 1
            # если долго не было файлов (человек перестал говорить)
            if last_speaking > float(await set_get_config_all("Sound", "delay_record")) * 10:
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
                    traceback_str = traceback.format_exc()
                    print(str(traceback_str))
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
                    traceback_str = traceback.format_exc()
                    print(str(traceback_str))
                    print(f"Ошибка при создании пустого аудиофайла: {e}")
                # вызов function
                if not text is None:
                    from function import replace_mat_in_sentence, replace_numbers_in_sentence
                    text = await replace_numbers_in_sentence(
                        text)
                    text = await replace_mat_in_sentence(text)
                    print(text)

                    if await set_get_config_all("dialog", "dialog", None) == "True":
                        spoken_text_config = await set_get_config_all("dialog", "user_spoken_text", None)
                        if spoken_text_config == "None":
                            spoken_text_config = ""
                        await set_get_config_all("dialog", "user_spoken_text", spoken_text_config + text)
                    else:
                        await set_get_config_all("Default", "user_name", value=ctx.author.name)
                        await run_main_with_settings(ctx,
                                                     await set_get_config_all("Default", "currentainame") + ", " + text,
                                                     True)

            continue

        # запись непустых файлов
        max_loudness_all = float('-inf')
        for file in file_found:
            volume = await max_volume(file)
            if volume == float('-inf'):
                Path(file).unlink()
                file_found.remove(file)
                continue
            if volume > max_loudness_all:
                max_loudness_all = volume

        if max_loudness_all > int(await set_get_config_all("Sound", "min_volume", None)):
            last_speaking = 0

            result = AudioSegment.from_file(wav_filename, format="wav")

            for file in file_found:
                result += AudioSegment.from_file(file, format="wav")

            try:
                result.export(wav_filename, format="wav")
            except Exception as e:
                traceback_str = traceback.format_exc()
                print(str(traceback_str))
                print(f"Ошибка при экспорте аудио: {e}")

        # удаление временного файла
        try:
            for file in file_found:
                Path(file).unlink()
        except FileNotFoundError:
            pass
    print("Stop_Recording")


async def get_file_type(ctx, attachment):
    if not attachment:
        await ctx.send("Файл не прикреплен.")
        return
    import magic
    mime = magic.Magic()
    file_type = mime.from_buffer(attachment.fp.read(2048))

    # Определить тип файла на основе MIME-типа
    if file_type.startswith('image'):
        return "image"
    elif file_type.startswith('video'):
        return "video"
    elif file_type.startswith('audio'):
        return "audio"
    else:
        await ctx.send("Неизвестный тип файла.")


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
            load_images1 = False
            load_images2 = False
            if len(arguments) > 2:
                args = arguments[2]
                if "gpt_local" in args:
                    load_gpt = True
                if "gpt_provider" in args:
                    set_get_config_all_not_async("gpt", "use_gpt_provider", "True")
                if "img1" in args:
                    load_images1 = True
                    set_get_config_all_not_async("Values", "cuda0_is_busy", "True")
                if "img2" in args:
                    load_images1 = True
                    set_get_config_all_not_async("Values", "cuda0_is_busy", "True")
                    load_images2 = True
                    set_get_config_all_not_async("Values", "cuda1_is_busy", "True")
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
                if set_get_config_all_not_async("gpt", "gpt") == "True":
                    break

        # == load images ==
        if load_images1:
            print("load image model on GPU-0")

            from image_create_cuda0 import generate_picture0

            pool = multiprocessing.Pool(processes=1)
            pool.apply_async(generate_picture0)
            pool.close()
            while True:
                time.sleep(0.5)
                if set_get_config_all_not_async("Image0", "model_loaded") == "True":
                    break
        if load_images2:
            print("load image model on GPU-1")

            from image_create_cuda1 import generate_picture1

            pool = multiprocessing.Pool(processes=1)
            pool.apply_async(generate_picture1)
            pool.close()
            while True:
                time.sleep(0.5)
                if set_get_config_all_not_async("Image1", "model_loaded") == "True":
                    break
        # === load voice models ===
        from only_voice_change_cuda0 import voice_change0
        from only_voice_change_cuda1 import voice_change1

        pool = multiprocessing.Pool(processes=2)
        pool.apply_async(voice_change0)
        # pool.apply_async(voice_change1)
        pool.close()

        # ==== load bot ====
        print("====load bot====")
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start(discord_token))
    except Exception as e:
        traceback_str = traceback.format_exc()
        print(str(traceback_str))
        print(f"Произошла ошибка: {e}")
