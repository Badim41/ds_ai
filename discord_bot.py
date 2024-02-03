import asyncio
import os
import random
import re
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path
from pydub import AudioSegment
from pytube import Playlist

import speech_recognition as sr

import discord
from cover_gen import run_ai_cover_gen
from discord import Option
from discord.ext import commands
from discord_tools.chat_gpt import ChatGPT
from discord_tools.detect_mat import moderate_mat_in_sentence
from discord_tools.logs import Logs, Color
from discord_tools.sql_db import set_get_database_async as set_get_config_all
from discord_tools.timer import Time_Count
from function import Image_Generator, Character, Voice_Changer, get_link_to_file
from modifed_sinks import StreamSink
from use_free_cuda import Use_Cuda

recognizers = {}
audio_players = {}
dialogs = {}
characters_all = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='\\', intents=intents)
cuda_manager = Use_Cuda()
image_generators = []

logger = Logs(warnings=True)

voiceChannelErrorText = '❗ Вы должны находиться в голосовом канале ❗'
ALL_VOICES = {'Rachel': "Ж", 'Clyde': 'М', 'Domi': 'Ж', 'Dave': 'М', 'Fin': 'М', 'Bella': 'Ж', 'Antoni': 'М',
              'Thomas': 'М',
              'Charlie': 'М', 'Emily': 'Ж', 'Elli': 'Ж', 'Callum': 'М', 'Patrick': 'М', 'Harry': 'М', 'Liam': 'М',
              'Dorothy': 'Ж', 'Josh': 'М', 'Arnold': 'М', 'Charlotte': 'Ж', 'Matilda': 'Ж', 'Matthew': 'М',
              'James': 'М',
              'Joseph': 'М', 'Jeremy': 'М', 'Michael': 'М', 'Ethan': 'М', 'Gigi': 'Ж', 'Freya': 'Ж', 'Grace': 'Ж',
              'Daniel': 'М', 'Serena': 'Ж', 'Adam': 'М', 'Nicole': 'Ж', 'Jessie': 'М', 'Ryan': 'М', 'Sam': 'М',
              'Glinda': 'Ж',
              'Giovanni': 'М', 'Mimi': 'Ж'}


class SQL_Keys:
    AIname = "AIname"
    reload = "reload"
    owner_id = "owner_id"
    delay_record = "delay_record"
    gpt_mode = "gpt_mode"

    # [Default]
    # reload
    # owner_id
    # AIname
    # delay_record
    # gpt_role
    # [User]
    # gpt_mode


class DiscordUser:
    def __init__(self, ctx):
        self.ctx = ctx
        self.id = ctx.author.id
        self.name = ctx.author.name
        character_name = asyncio.run(set_get_config_all(self.id, SQL_Keys.AIname))
        self.character = Character(character_name)
        self.gpt_mode = asyncio.run(set_get_config_all(self.id, SQL_Keys.gpt_mode))
        self.owner = asyncio.run(set_get_config_all("Default", SQL_Keys.owner_id)) == str(self.id)

    async def set_user_config(self, key, value=None):
        await set_get_config_all(self.id, key, value)
        await self.update_values()

    async def update_values(self):
        self.gpt_mode = await set_get_config_all(self.id, SQL_Keys.gpt_mode)
        character_name = await set_get_config_all(self.id, SQL_Keys.AIname)
        self.character = Character(character_name)


@bot.event
async def on_ready():
    logger.logging('Status: online', Color.GREEN)
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name='AI-covers'))
    id = await set_get_config_all("Default", SQL_Keys.owner_id)
    logger.logging("ID:", id, Color.GRAY)
    if not id == "True":
        user = await bot.fetch_user(int(id))
        await user.send("Перезагружен!")


@bot.event
async def on_message(message):
    ctx = await bot.get_context(message)

    if message.author.id == 1165023027847757836:  # minecraft chat bot
        text = message.content
        if text.startswith("\\themer "):
            text = text.replace("\\themer ", "")

            guild_id = ctx.guild.id
            if guild_id in dialogs:
                dialog = next((rec for rec in dialogs[guild_id] if rec.ctx == ctx), None)
                if dialog:
                    dialog.theme = text
                    await ctx.send("Изменена тема:" + text)
            return

        _, text = await moderate_mat_in_sentence(text)

        user = text[:text.find(":")]
        if "[" in text and "]" in text:
            text = re.sub(r'[.*?]', '', text)
        chatGPT = ChatGPT()
        answer = await chatGPT.run_all_gpt(f"{user}:{text}", user_id=user)
        await ctx.send(answer)
        return

    # other users
    if message.author.bot:
        return
    if bot.user in message.mentions:
        text = message.content
        try:
            # получение, на какое сообщение ответили
            if message.reference:
                referenced_message = await message.channel.fetch_message(message.reference.message_id)
                reply_on_message = referenced_message.content
                if "||" in reply_on_message:
                    reply_on_message = re.sub(r'\|\|.*?\|\|', '', reply_on_message)
                text += f" (Пользователь отвечает на ваше сообщение \"{reply_on_message}\")"

            _, text_out = await moderate_mat_in_sentence(text)

            user = DiscordUser(ctx)
            gpt_role = user.character.gpt_info

            chatGPT = ChatGPT()
            answer = await chatGPT.run_all_gpt(f"{user.name}:{text}", user_id=user.id, gpt_role=gpt_role)
            await ctx.send(answer)
            audio_player = AudioPlayerDiscord(ctx)
            if audio_player.voice_client and user.character:
                await user.character.text_to_speech(answer)
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.logging(str(traceback_str), Color.RED)
            await ctx.send(f"Ошибка при команде say с параметрами {message}: {e}")
    await bot.process_commands(message)


@bot.slash_command(name="help", description='помощь по командам')
async def help_command(
        ctx,
        command: Option(str, description='Нужная вам команда', required=True,
                        choices=['say', 'read_messages', 'ai_cover', 'tts', 'add_voice', 'create_dialog',
                                 'change_image', 'change_video', 'join', 'disconnect', 'record', 'stop_recording',
                                 'pause', 'skip']
                        ),
):
    if command == "say":
        await ctx.respond("# /say\n(Сделать запрос к GPT)\n**text - запрос для GPT**\ngpt_mode\*:\n- много ответов\n")
        await ctx.send("\* - параметр сохраняется")
    elif command == "read_messages":
        await ctx.respond("# /read_messages\n(Прочитать последние сообщения и что-то с ними сделать)\n**number - "
                          "количество читаемых сообщений**\n**prompt - запрос (например, перескажи эти сообщения)**\n")
    elif command == "ai_cover":
        await ctx.respond(
            "# /ai_cover:\n(Перепеть/озвучить видео или аудио)\n**url - ссылка на видео**\n**audio_path - "
            "аудио файл**\nvoice - голосовая модель\ngender - пол (для тональности)\npitch - тональность (12 "
            "из мужского в женский, -12 из женского в мужской)\nindexrate - индекс голоса (чем больше, тем больше "
            "черт черт голоса говорящего)\nrms_mix_rate - количество шума (чем больше, тем больше шума)\nfilter_radius - "
            "размер фильтра (чем больше, тем больше шума)\nmain_vocal, back_vocal, music - громкость каждой "
            "аудиодорожки\nroomsize, wetness, dryness - параметры реверберации\npalgo - rmvpe - лучший, mangio-crepe "
            "- более плавный\nhop - длина для учитывания тональности (mangio-crepe)\ntime - продолжительность (для "
            "войс-чата)\nstart - время начала (для войс-чата)\noutput - link - сслыка на архив, all_files - все "
            "файлы, file - только финальный файл\nonly_voice_change - просто заменить голос, без разделения вокала "
            "и музыки\n")
    elif command == "tts":
        await ctx.respond(
            "# /tts\n(Озвучить текст)\n**text - произносимый текст**\nvoice_name - голосовая модель\nspeed - "
            "Ускорение/замедление\nvoice_model - Модель голоса elevenlab\noutput - Отправляет файл в чат\n"
            "stability - Стабильность голоса (0 - нестабильный, 1 - стабильный)\*\n"
            "similarity_boost - Повышение сходства (0 - отсутствует)\*\n"
            "style - Выражение (0 - мало пауз и выражения, 1 - большое количество пауз и выражения)\*\n")
        await ctx.send("\* - параметр сохраняется")
    elif command == "add_voice":
        await ctx.respond("# /add_voice\n(Добавить голосовую модель)\n**url - ссылка на модель **\n**name - имя модели "
                          "**\n**gender - пол модели (для тональности)**\ninfo - информация о человеке (для запроса GPT)\n"
                          "speed - ускорение/замедление при /tts\nvoice_model - модель elevenlab\nchange_voice - True = "
                          "заменить на текущий голос\ntxt_file - быстрое добавление множества голосовых моделей *(остальные аргументы как 'url', 'gender', 'name'  будут игнорироваться)*, для использования:\n"
                          "- напишите в txt файле аргументы для add_voice (1 модель - 1 строка), пример:")
        await send_file(ctx, "add_voice_args.txt")
    elif command == "create_dialog":
        await ctx.respond(
            "# /create_dialog\n(Создать диалог в войс-чате, используйте join)\n**names - участники диалога "
            "через ';' - список голосовых моделей Например, Участник1;Участник2**\ntheme - Тема разговора "
            "(может измениться)\nprompt - Постоянный запрос (например, что они находятся в определённом месте)\n")
    elif command == "change_image":
        await ctx.respond("# /change_image \n(Изменить изображение)\n**image - картинка, которую нужно изменить**\n"
                          "**prompt - Запрос **\nnegative_prompt - Негативный запрос\nsteps - Количество шагов (больше - "
                          "лучше, но медленнее)\nseed - сид (если одинаковый сид и файл, то получится то же самое изображение)"
                          "\nx - расширение по X\ny - расширение по Y\nstrength - сила изменения\nstrength_prompt - сила для "
                          "запроса\nstrength_negative_prompt - сила для негативного запроса\nrepeats - количество изображений "
                          "(сид случайный!)\n")
    elif command == "change_video":
        await ctx.respond(
            "# /change_video \n(Изменить видео **ПОКАДРОВО**)\n**video_path - видеофайл**\n**fps - Количество "
            "кадров в секунду**\n**extension - Качество видео **\n**prompt - Запрос**\nnegative_prompt - "
            "Негативный запрос\nsteps - Количество шагов (больше - лучше, но медленнее)\nseed - сид (если "
            "одинаковый сид и файл, то получится то же самое изображение)\nstrength - сила изменения\n"
            "strength_prompt - сила для запроса\nstrength_negative_prompt - сила для негативного запроса\n"
            "voice - голосовая модель\npitch - тональность (12 из мужского в женский, -12 из женского в "
            "мужской)\nindexrate - индекс голоса (чем больше, тем больше черт черт голоса говорящего)\n"
            "rms_mix_rate - количество шума (чем больше, тем больше шума)\nfilter_radius - размер фильтра (чем "
            "больше, тем больше шума)\nmain_vocal, back_vocal, music - громкость каждой аудиодорожки\n"
            "roomsize, wetness, dryness - параметры реверберации\n")
    elif command == "join":
        await ctx.respond("# /join\n - присоединиться к вам в войс-чате")
    elif command == "disconnect":
        await ctx.respond("# /disconnect\n - выйти из войс-чата")
    elif command == "record":
        await ctx.respond("# /record\n - включить распознавание речи через микрофон")
    elif command == "stop_recording":
        await ctx.respond("# /stop_recording\n  - выключить распознавание речи через микрофон")
    elif command == "pause":
        await ctx.respond("# /pause\n - пауза / завершение диалога")
    elif command == "skip":
        await ctx.respond("# /skip\n - пропуск аудио")


@bot.slash_command(name="config", description='изменить конфиг')
async def __config(
        ctx,
        section: Option(str, description='секция', required=True),
        key: Option(str, description='ключ', required=True),
        value: Option(str, description='значение', required=False, default=None)
):
    try:
        await ctx.defer()
        owner_id = await set_get_config_all("Default", SQL_Keys.owner_id)
        if not ctx.author.id == int(owner_id):
            await ctx.author.send("Доступ запрещён")
            return
        result = await set_get_config_all(section, key, value)
        if value is None:
            await ctx.respond(result)
        else:
            await ctx.respond(section + " " + key + " " + value)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
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
    try:
        messages = []
        async for message in ctx.channel.history(limit=number):
            messages.append(f"Сообщение от {message.author.name}: {message.content}")
        # От начала до конца
        messages = messages[::-1]
        # убираем последнее / последние сообщения
        messages = messages[:number - 1]
        chatGPT = ChatGPT()
        answer = await chatGPT.run_all_gpt(f"{prompt}. Вот история сообщений:{messages}", user_id=0)
        await ctx.respond(answer)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        await ctx.respond(f"Произошла ошибка: {e}")


@bot.slash_command(name="join", description='присоединиться к голосовому каналу')
async def join(ctx):
    await ctx.defer()
    await AudioPlayerDiscord(ctx).join_channel()
    await ctx.respond("Присоединяюсь")


@bot.slash_command(name="disconnect", description='выйти из войс-чата')
async def disconnect(ctx):
    await ctx.defer()
    await AudioPlayerDiscord(ctx).disconnect()
    await ctx.respond("Покидаю войс-чат")


@bot.slash_command(name="pause", description='пауза/воспроизведение (остановка диалога)')
async def pause(ctx):
    await ctx.defer()
    guild_id = ctx.guild.id
    if guild_id in dialogs:
        dialog = next((rec for rec in dialogs[guild_id] if rec.ctx == ctx), None)
        if dialog:
            await dialog.stop_dialog()
            await ctx.respond("Остановлен диалог")
    await AudioPlayerDiscord(ctx).stop()
    await ctx.respond("Пауза")


@bot.slash_command(name="skip", description='пропуск аудио')
async def skip(ctx):
    await ctx.defer()
    await AudioPlayerDiscord(ctx).skip()
    await ctx.respond("Остановлено")


@bot.slash_command(name="say", description='Сказать роботу что-то')
async def __say(
        ctx,
        text: Option(str, description='Сам текст/команда. Список команд: \\help-say', required=True),
        gpt_mode: Option(str, description="модификация GPT. Модификация сохраняется при следующих запросах!",
                         choices=["быстрый режим", "много ответов (медленный)", "экономный режим"], required=False,
                         default=None)
):
    # ["fast", "all", "None"], ["быстрый режим", "много ответов (медленный)", "Экономный режим"]
    user = DiscordUser(ctx)
    if gpt_mode:
        gpt_mode = gpt_mode.replace("быстрый режим", "Fast").replace("много ответов (медленный)", "All").replace(
            "экономный режим", "None")
        await user.set_user_config(SQL_Keys.gpt_mode, gpt_mode)
    else:
        gpt_mode = user.gpt_mode

    try:
        await ctx.respond('Выполнение...')
        if not gpt_mode:
            gpt_mode = "Fast"
        _, text = await moderate_mat_in_sentence(text)

        gpt_role = user.character.gpt_info

        chatGPT = ChatGPT()
        answer = await chatGPT.run_all_gpt(f"{user.name}:{text}", user_id=user.id, gpt_role=gpt_role, mode=gpt_mode)
        await ctx.send(answer)
        audio_player = AudioPlayerDiscord(ctx)
        if audio_player.voice_client and user.character:
            await user.character.text_to_speech(answer)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        await ctx.respond(f"Ошибка при команде say (с параметрами{text}): {e}")


async def get_voice_list():
    from cover_gen import rvc_models_dir
    directory_path = rvc_models_dir

    # Получение имен папок
    return [folder for folder in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, folder))]


@bot.slash_command(name="tts", description='Заставить бота говорить всё, что захочешь')
async def __tts(
        ctx,
        text: Option(str, description='Текст для озвучки', required=True),
        voice_name: Option(str, description='Голос для озвучки', required=False, default=None),
        speed: Option(float, description='Ускорение голоса', required=False, default=None, min_value=1, max_value=3),
        voice_model_eleven: Option(str, description=f'Какая модель elevenlabs будет использована', required=False,
                                   default=None),
        stability: Option(float, description='Стабильность голоса', required=False, default=None, min_value=0,
                          max_value=1),
        similarity_boost: Option(float, description='Повышение сходства', required=False, default=None, min_value=0,
                                 max_value=1),
        style: Option(float, description='Выражение', required=False, default=None, min_value=0, max_value=1),
        output: Option(str, description='Отправить результат', required=False,
                       choices=["1 файл (RVC)", "2 файла (RVC & elevenlabs/GTTS)", "None"], default="1 файл (RVC)"),
        pitch: Option(int, description="Изменить тональность", required=False, default=0, min_value=-24,
                      max_value=24)
):
    user = DiscordUser(ctx)
    if not voice_name:
        voice_name = user.character.name
    elif not user.character.name == voice_name:
        await ctx.send("Обновлена базовая модель на:" + voice_name)
        await user.set_user_config(SQL_Keys.AIname, voice_name)

    voices = await get_voice_list()
    if voice_name not in voices:
        return await ctx.response.send_message("Выберите голос из списка: " + ';'.join(voices))

    voice_models = None
    if voice_model_eleven == "All":
        voice_models = ALL_VOICES.values()
    elif voice_model_eleven:
        if voice_models not in ALL_VOICES.values():
            await ctx.response.send_message("Список голосов elevenlabs: \n" + ';'.join(ALL_VOICES.values()))
            return
    character = Character(voice_name)

    try:

        await ctx.response.send_message('Выполнение...' + voice_name)
        cuda_number = await cuda_manager.use_cuda()
        await character.load_voice(cuda_number, speed=speed, stability=stability, similarity_boost=similarity_boost,
                                   style=style, pitch=pitch)
        for voice_model in voice_models:
            timer = Time_Count()
            character.voice_model_eleven = voice_model
            mat_found, text = await moderate_mat_in_sentence(text)
            if mat_found:
                await ctx.respond("Такое точно нельзя произносить!")
                return
            # запускаем TTS
            await character.text_to_speech(text, audio_path=f"{ctx.author.id}.mp3")
            # перестаём использовать видеокарту

            await ctx.respond("Потрачено на обработку:" + timer.count_time())
            if output:
                if output.startswith("1"):
                    await send_file(ctx, f"{voice_model}.mp3")
                elif output.startswith("2"):
                    await send_file(ctx, "1.mp3")
                    await send_file(ctx, f"{voice_model}.mp3")
        await cuda_manager.stop_use_cuda(cuda_number)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        await ctx.respond(f"Ошибка при озвучивании текста (с параметрами {text}): {e}")
        # перестаём использовать видеокарту
        await cuda_manager.stop_use_cuda(cuda_number)


async def send_output(ctx, audio_path, output, timer):
    await ctx.send("===Файлы " + os.path.basename(audio_path)[:-4] + "===")
    output = output.replace(" ", "")
    # конечный файл
    if output == "file":
        await send_file(ctx, audio_path)
    # все файлы
    elif output == "all_files":
        for filename in os.listdir(os.path.dirname(audio_path)):
            file_path = os.path.join(os.path.dirname(audio_path), filename)
            await send_file(ctx, file_path, delete_file=True)
    # zip файл по ссылке
    elif output == "link":
        zip_name = os.path.dirname(audio_path) + f"/all_files.zip"
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in os.listdir(os.path.dirname(audio_path)):
                file_path = os.path.join(os.path.dirname(audio_path), filename)
                if ".zip" in file_path:
                    continue
                zipf.write(file_path, os.path.basename(file_path))
        link = await get_link_to_file(zip_name, ctx)
        await ctx.send(f"Ссылка на скачку:{link}")
    await logger.logging("Играет " + os.path.basename(audio_path)[:-4], Color.GREEN)
    audio_player = AudioPlayerDiscord(ctx)
    await audio_player.play(audio_path)

    if not output == "None":
        await ctx.send(timer.count_time())

    else:
        await ctx.send("Произошла ошибка")


async def run_ai_cover_gen_several_cuda(song_input, rvc_dirname, pitch, index_rate, filter_radius, rms_mix_rate,
                                        protect, pitch_detection_algo,
                                        crepe_hop_length, main_vol, backup_vol,
                                        inst_vol, reverb_size, reverb_wetness, reverb_dryness,
                                        reverb_damping,
                                        output_format, output, ctx):
    cuda_number = await cuda_manager.use_cuda()
    timer = Time_Count()
    audio_path = await run_ai_cover_gen(song_input=song_input, rvc_dirname=rvc_dirname, pitch=pitch,
                                        index_rate=index_rate,
                                        filter_radius=filter_radius, rms_mix_rate=rms_mix_rate, protect=protect,
                                        pitch_detection_algo=pitch_detection_algo,
                                        crepe_hop_length=crepe_hop_length, main_vol=main_vol, backup_vol=backup_vol,
                                        inst_vol=inst_vol, reverb_size=reverb_size, reverb_wetness=reverb_wetness,
                                        reverb_dryness=reverb_dryness,
                                        reverb_damping=reverb_damping,
                                        output_format=output_format, cuda_number=cuda_number)
    await send_output(ctx=ctx, audio_path=audio_path, output=output, timer=timer)
    await cuda_manager.stop_use_cuda(cuda_number)


@bot.slash_command(name="ai_cover", description='Заставить бота озвучить видео/спеть песню')
async def __cover(
        ctx,
        url: Option(str, description='Ссылка на видео', required=False, default=None),
        audio_path: Option(discord.SlashCommandOptionType.attachment, description='Аудиофайл',
                           required=False, default=None),
        voice_name: Option(str, description='Голос для видео', required=False, default=None),
        pitch: Option(int, description='Какую использовать тональность (от -24 до 24) (или указать gender)',
                      required=False,
                      default=None, min_value=-24, max_value=24),
        indexrate: Option(float, description='Индекс голоса (от 0 до 1)', required=False, default=0.5, min_value=0,
                          max_value=1),
        rms_mix_rate: Option(float, description='Громкость шума (от 0 до 1)', required=False, default=0.4, min_value=0,
                             max_value=1),
        filter_radius: Option(int,
                              description='Насколько далеко от каждой точки в данных будут учитываться значения... (от 1 до 7)',
                              required=False, default=3, min_value=0,
                              max_value=7),
        main_vocal: Option(int, description='Громкость основного вокала (от -50 до 0)', required=False, default=0,
                           min_value=-50, max_value=0),
        back_vocal: Option(int, description='Громкость бэквокала (от -50 до 0)', required=False, default=0,
                           min_value=-50, max_value=0),
        music: Option(int, description='Громкость музыки (от -50 до 0)', required=False, default=0, min_value=-50,
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
        output: Option(str, description='Отправить результат',
                       choices=["ссылка на все файлы", "только результат (1 файл)", "все файлы", "не отправлять"],
                       required=False, default="только результат (1 файл)"),
        only_voice_change: Option(bool,
                                  description='Не извлекать инструментал и бэквокал, изменить голос. Не поддерживаются ссылки',
                                  required=False, default=False)
):
    async def get_links_from_playlist(playlist_url):
        try:
            playlist = Playlist(playlist_url)
            playlist._video_regex = re.compile(r"\"url\":\"(/watch\?v=[\w-]*)")
            video_links = playlist.video_urls
            video_links = str(video_links).replace("'", "").replace("[", "").replace("]", "").replace(" ", "").replace(
                ",",
                ";")
            return video_links
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.logging(str(traceback_str), Color.RED)
            logger.logging(f"Произошла ошибка при извлечении плейлиста", Color.RED)
            return []

    param_string = None
    # ["link", "file", "all_files", "None"], ["ссылка на все файлы", "только результат (1 файл)", "все файлы", "не отправлять"]
    output = output.replace("ссылка на все файлы", "link").replace("только результат (1 файл)", "file").replace(
        "все файлы", "all_files").replace("не отправлять", "None")
    try:
        await ctx.defer()
        await ctx.respond('Выполнение...')
        voices = await get_voice_list()
        user = DiscordUser(ctx)

        if voice_name is None:
            voice_name = user.character.name
            if voice_name is None:
                voice_name = await set_get_config_all("Default", SQL_Keys.AIname)
                if voice_name is None:
                    await ctx.respond("Выберите голос для озвучки:", ', '.join(voices))
                    return
        elif voice_name not in voices:
            await ctx.respond("Выберите голос для озвучки:", ', '.join(voices))
            return

        if pitch is None:
            pitch = user.character.pitch

        logger.logging("suc params", Color.CYAN)

        urls = []
        if audio_path:
            filename = f"{ctx.author.id}-{random.randint(1, 1000000)}.mp3"
            await audio_path.save(filename)
            urls.append(filename)
            if only_voice_change:
                cuda = await cuda_manager.use_cuda()
                voice_changer = Voice_Changer(cuda_number=cuda, voice_name=voice_name, index_rate=indexrate,
                                              pitch=pitch, filter_radius=filter_radius, rms_mix_rate=rms_mix_rate,
                                              protect=0.3, algo=palgo)
                await voice_changer.voice_change(input_path=filename, output_path=filename)
                await send_file(ctx, file_path=filename)
                await cuda_manager.stop_use_cuda(cuda)
                return
        if url:
            if ";" in url:
                urls += url.split(";")
            elif "playlist" in url:
                urls += (await get_links_from_playlist(url)).split(";")

        for i, url in enumerate(urls):
            asyncio.ensure_future(
                run_ai_cover_gen_several_cuda(song_input=url, rvc_dirname=voice_name, pitch=pitch, index_rate=indexrate,
                                              filter_radius=filter_radius, rms_mix_rate=rms_mix_rate, protect=0.3,
                                              pitch_detection_algo=palgo,
                                              crepe_hop_length=hop, main_vol=main_vocal, backup_vol=back_vocal,
                                              inst_vol=music, reverb_size=roomsize, reverb_wetness=wetness,
                                              reverb_dryness=dryness,
                                              reverb_damping=0.7,
                                              output_format='mp3', output=output, ctx=ctx))
        if not urls:
            await ctx.respond('Не указана ссылка или аудиофайл')
            return

    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        await ctx.respond(f"Ошибка при изменении голоса(ID:d5) (с параметрами {param_string}): {e}")


class Dialog_AI:
    def __init__(self, ctx, characters, theme, global_prompt):
        self.alive = True
        self.ctx = ctx

        dialogs[self.ctx.guild.id].append(self)

        self.characters = []
        self.names = []
        self.infos = []

        for i, name in enumerate(characters):
            character = Character(name=name)
            character.load_voice(i % 2)
            self.characters.append(character)
            self.names.append(character.name)
            self.infos.append(character.info)

        self.theme = theme
        self.global_prompt = global_prompt
        self.audio_player = AudioPlayerDiscord(ctx)
        self.audio_player.join_channel()

        self.recognizer = Recognizer(ctx=ctx, with_gpt=False)

        self.play_number = 0
        self.files_number = 0
        self.gpt = ChatGPT(openAI_keys=False, openAI_moderation=False, auth_keys=False)
        self.user_id = ctx.author.id * 10

        self.dialog_create = {}
        self.dialog_play = {}

        asyncio.ensure_future(self.gpt_dialog())
        asyncio.ensure_future(self.play_dialog())
        functions = [self.create_audio_dialog(character) for character in self.characters]
        for function in functions:
            asyncio.ensure_future(function)

    async def stop_dialog(self):
        if self.ctx.guild.id in dialogs:
            dialogs[self.ctx.guild.id].remove(self)
            self.alive = False

    async def play_dialog(self):
        while self.alive:
            if self.dialog_play[self.play_number]:
                name, audio_path = self.dialog_play[self.play_number]
                del self.dialog_play[self.play_number]

                self.play_number += 1

                await self.ctx.send("говорит " + name)
                await self.audio_player.play(audio_path)
                os.remove(audio_path)
            else:
                logger.logging("warn: Нет аудио для диалога!", Color.RED)
                await asyncio.sleep(0.75)

    async def create_audio_dialog(self, character):
        while self.alive:
            files_number = self.files_number
            text = self.dialog_create[files_number][character.name]
            if text:
                audio_path = f"{self.files_number}{character.name}.mp3"
                character.text_to_speech(text=text, audio_path=audio_path, output_name=audio_path)
                del self.dialog_create[files_number][character.name][text]
                self.dialog_play[files_number] = (character.name, audio_path)
            await asyncio.sleep(0.5)

    async def save_dialog(self, result):
        logger.logging(result, Color.GRAY)
        with open(f"caversAI/history-{self.ctx.guild.id}", "a", encoding="utf-8") as writer:
            for line in result.split("\n"):
                for name in self.names:
                    # Человек: привет
                    # Человек (man): привет
                    # Чэловек: привет
                    if (line.startswith(name) or line.startswith(name.replace("э", "е"))) and ":" in line:
                        line = line[line.find(":") + 1:]
                        self.dialog_create[self.files_number][name] = line
                        writer.write(f"{name}:{line}\n")
                        self.files_number += 1
                        break

    async def run_gpt(self, prompt):
        result = await self.gpt.run_all_gpt(prompt=prompt, user_id=self.user_id)
        if "(" in result and ")" in result:
            result = re.sub(r'\(.*?\)', '', result)
        return result.replace("[", "").replace("]", "").replace(
            "Привет, ребята! ", "").replace("Привет, ребята", "").replace("Всем привет, ", "").replace("Эй", "")

    async def gpt_dialog(self):
        prompt = (
            f"Привет, chatGPT. Вы собираетесь сделать диалог между {', '.join(self.names)}. На тему \"{self.theme}\". "
            f"персонажи должны соответствовать своему образу насколько это возможно. "
            f"{'.'.join(self.infos)}. {self.global_prompt}. "
            f"Обязательно в конце диалога напиши очень кратко что произошло в этом диалоги и что должно произойти дальше. "
            f"Выведи диалог в таком формате:[Говорящий]: [текст, который он произносит]")
        result = await self.run_gpt(prompt)
        if "*" in result:
            result = re.sub(r'\*.*?\*', '', result)

        await self.save_dialog(result)

        theme_last = self.theme
        while self.alive:
            try:
                if "**" in result:
                    result = result[result.rfind("**"):400]
                elif "\n" in result:
                    result = result[result.rfind("\n"):400]

                spoken_text = self.recognizer.recognized
                if spoken_text:
                    spoken_text = "Зрители за прошлый диалог написали:\"" + spoken_text + "\""
                    self.recognizer.recognized = ""

                # Тема добавляется в запрос, если она изменилась
                new_theme = self.theme
                if not theme_last == new_theme:
                    theme_last = new_theme
                    theme_temp = " на тему" + new_theme
                    with open(f"caversAI/history-{self.ctx.guild.id}", "a", encoding="utf-8") as writer:
                        writer.write(f"\n==Новая тема==: {new_theme}\n\n")
                else:
                    theme_temp = f"Изначальная тема диалога была {new_theme}, не сильно отходи от её"

                prompt = (f"Привет chatGPT, продолжи диалог между {', '.join(self.names)}{theme_temp}. "
                          f"{'.'.join(self.infos)}. {self.global_prompt} "
                          f"персонажи должны соответствовать своему образу насколько это возможно. "
                          f"Никогда не пиши приветствие в начале этого диалога. "
                          f"Никогда не повторяй то, что было в прошлом диалоге! Вот что было в прошлом диалоге:\"{result}\". {spoken_text}"
                          f"\nОбязательно в конце напиши очень кратко что произошло в этом диалоги и что должно произойти дальше. "
                          f"Выведи диалог в таком формате:[Говорящий]: [текст, который он произносит]")

                result = await self.run_gpt(prompt)

                await self.save_dialog(result)

                # слишком большой разрыв
                while self.files_number - self.play_number > 4:
                    logger.logging("wait, difference > 4", Color.YELLOW)
                    await asyncio.sleep(2.5)
                    if not self.alive:
                        return

                # Слишком много текста
                while len(self.dialog_create) > 2:
                    logger.logging("wait, too many text > 2", Color.YELLOW)
                    await asyncio.sleep(2.5)
                    if not self.alive:
                        return

            except Exception as e:
                traceback_str = traceback.format_exc()
                logger.logging(str(traceback_str), Color.RED)
                await self.ctx.send(f"Ошибка при изменении голоса(ID:d4): {e}")


@bot.slash_command(name="add_voice", description='Добавить RVC голос')
async def __add_voice(
        ctx,
        url: Option(str, description='Ссылка на .zip файл с моделью RVC', required=True),
        name: Option(str, description=f'Имя модели', required=True),
        gender: Option(str, description=f'Пол (для настройки тональности)', required=True,
                       choices=['мужчина', 'женщина']),
        pitch: Option(int, description="Какую использовать тональность (от -24 до 24) (или указать gender)",
                      required=False, default=0, min_value=-24, max_value=24),
        info: Option(str, description=f'Какие-то сведения о данном человеке', required=False,
                     default="Отсутствует"),
        speed: Option(float, description=f'Ускорение/замедление голоса', required=False,
                      default=1, min_value=1, max_value=3),
        voice_model_eleven: Option(str, description=f'Какая модель elevenlabs будет использована', required=False,
                                   default="Adam"),
        change_voice: Option(bool, description=f'(необязательно) Изменить голос на этот', required=False,
                             default=False),
        txt_file: Option(discord.SlashCommandOptionType.attachment,
                         description='Файл txt для добавления нескольких моделей сразу',
                         required=False, default=None)
):
    if voice_model_eleven not in ALL_VOICES.values():
        await ctx.respond("Список голосов: \n" + '; '.join(ALL_VOICES.values()))
        return
    await ctx.defer()
    await ctx.respond('Выполнение...')
    if txt_file:
        urls, names, genders, infos, speeds, voice_model_elevens, stabilities, similarity_boosts, styles = await agrs_with_txt(
            txt_file)
        logger.logging("url:", urls)
        logger.logging("name:", names)
        logger.logging("gender:", genders)
        logger.logging("info:", infos)
        logger.logging("speed:", speeds)
        logger.logging("voice_model_eleven:", voice_model_elevens)
        logger.logging("stabilities:", stabilities)
        logger.logging("similarity_boosts:", similarity_boosts)
        logger.logging("styles:", styles)
        for i in range(len(urls)):
            if names[i] is None:
                await ctx.send(f"Не указано имя в {i + 1} моделе")
                continue
            if urls[i] is None:
                await ctx.send(f"Не указана ссылка в {i + 1} моделе ({name})")
                continue
            if genders[i] is None:
                await ctx.send(f"Не указан пол в {i + 1} моделе ({name})")
                continue
            await download_voice(ctx, urls[i], names[i], genders[i], infos[i], speeds[i], voice_model_elevens[i], False,
                                 stability=stabilities[i], similarity_boost=similarity_boosts[i], style=styles[i])
        await ctx.send("Все модели успешно установлены!")
        return
    if pitch is None:
        pitch = gender
    await download_voice(ctx, url, name, pitch, info, speed, voice_model_eleven, change_voice)


async def agrs_with_txt(txt_file):
    try:
        filename = "temp_args.txt"
        await txt_file.save(filename)
        with open(filename, "r", encoding="utf-8") as file:
            lines = file.readlines()
            lines[-1] = lines[-1] + " "
        url = []
        name = []
        gender = []
        info = []
        speed = []
        voice_model_eleven = []
        stability, similarity_boost, style = [], [], []
        for line in lines:
            if line.strip():
                # забейте, просто нужен пробел и всё
                line += " "
                line = line.replace(": ", ":")
                # /add_voice url:url_to_model name:some_name gender:мужчина info:some_info speed:some_speed voice_model_eleven:some_model
                pattern = r'(\w+):(.+?)\s(?=\w+:|$)'

                matches = re.findall(pattern, line)
                arguments = dict(matches)

                url.append(arguments.get('url', None))
                name.append(arguments.get('name', None))
                gender.append(arguments.get('gender', None))
                info.append(arguments.get('info', "Отсутствует"))
                speed.append(arguments.get('speed', "1"))
                voice_model_eleven.append(arguments.get('voice_model_eleven', "James"))
                stability.append(arguments.get('stability', "0.4"))
                similarity_boost.append(arguments.get('similarity_boost', "0.25"))
                style.append(arguments.get('style', "0.4"))
        return url, name, gender, info, speed, voice_model_eleven, stability, similarity_boost, style
    except Exception:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        return None, None, None, None, None, None, None, None, None


async def download_voice(ctx, url, name, gender, info, speed, voice_model_eleven, change_voice, stability="0.4",
                         similarity_boost="0.25", style="0.4"):
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
            voice_model_eleven,
            str(speed),
            stability,
            similarity_boost,
            style
        ]
        subprocess.run(command, check=True)
        if change_voice:
            user = DiscordUser(ctx)
            await user.set_user_config(SQL_Keys.AIname, name)
        await ctx.send(f"Модель {name} успешно установлена!")
    except subprocess.CalledProcessError as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        await ctx.respond("Ошибка при скачивании голоса.")


@bot.command(aliases=['cmd'], help="командная строка")
async def command_line(ctx, *args):
    owner_id = await set_get_config_all("Default", SQL_Keys.owner_id)
    if not ctx.author.id == int(owner_id):
        await ctx.author.send("Доступ запрещён")
        return

    # Получение объекта пользователя по ID
    text = " ".join(args)
    logger.logging("command line:", text)
    try:
        process = subprocess.Popen(text, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        for line in stdout.decode().split('\n'):
            if line.strip():
                await ctx.author.send(line)
        for line in stderr.decode().split('\n'):
            if line.strip():
                await ctx.author.send(line)
    except subprocess.CalledProcessError as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        await ctx.author.send(f"Ошибка выполнения команды: {e}")
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        await ctx.author.send(f"Произошла неизвестная ошибка: {e}")


@bot.command(aliases=['themer'], help="тема для диалога")
async def themer_set(ctx, *args):
    text = " ".join(args)
    guild_id = ctx.guild.id
    if guild_id in dialogs:
        dialog = next((rec for rec in dialogs[guild_id] if rec.ctx == ctx), None)
        if dialog:
            dialog.theme = text
            await ctx.send("Изменена тема:" + text)


@bot.slash_command(name="record", description='воспринимать команды из микрофона')
async def record(ctx):
    guild_id = ctx.guild.id

    if guild_id not in recognizers:
        recognizers[guild_id] = []

    if any(rec.ctx == ctx for rec in recognizers[guild_id]):
        await ctx.respond("Уже слушаю вас")
        return

    voice = ctx.author.voice
    if not voice:
        return await ctx.respond(voiceChannelErrorText)
    recognizer = Recognizer(ctx)
    asyncio.ensure_future(recognizer.recognize())


@bot.slash_command(name="stop_recording", description='перестать воспринимать команды из микрофона')
async def stop_recording(ctx):
    guild_id = ctx.guild.id

    if guild_id in recognizers:
        recognizer = next((rec for rec in recognizers[guild_id] if rec.ctx == ctx), None)
        if recognizer:
            await recognizer.stop_recording()
            await ctx.respond("Остановка записи.")
        else:
            await ctx.respond("Я и так тебя не слышал ._.")
    else:
        await ctx.respond("Я и так тебя не слышал ._.")


class Recognizer:
    def __init__(self, ctx, with_gpt=True):
        self.alive = True
        self.ctx = ctx
        self.stream_sink = StreamSink(ctx=ctx)
        self.google_recognizer = sr.Recognizer()
        self.last_speaking = 0
        self.delay_record = float(asyncio.run(set_get_config_all("Default", SQL_Keys.delay_record))) * 10
        self.user = DiscordUser(ctx)

        self.with_gpt = with_gpt
        self.recognized = ""

        voice = self.ctx.author.voice
        voice_channel = voice.channel

        if self.ctx.voice_client is None:
            self.vc = asyncio.run(voice_channel.connect())
        else:
            self.vc = self.ctx.voice_client

        recognizers[self.ctx.guild.id].append(self)
        self.stream_sink.set_user(self.ctx.author.id)
        self.vc.start_recording(
            self.stream_sink,
            None,
            self.ctx.channel
        )

        asyncio.run(self.ctx.respond("Внимательно вас слушаю"))

    async def stop_recording(self):
        if self.ctx.guild.id in recognizers:
            self.vc.stop_recording()
            recognizers[self.ctx.guild.id].remove(self)
            self.alive = False

    async def recognize(self):
        file_found = self.stream_sink.buffer.previous_audio_filename
        wav_filename = f"out_all{self.ctx.author.id}.wav"
        google_recognizer = self.google_recognizer
        while self.alive:
            speaking = self.stream_sink.buffer.speaking
            if not speaking:

                await asyncio.sleep(0.1)
                self.last_speaking += 1
                # если долго не было файлов (человек перестал говорить)
                if self.last_speaking > self.delay_record:
                    text = None
                    # очищаем поток
                    self.stream_sink.cleanup()
                    self.last_speaking = 0
                    # распознание речи
                    try:
                        with sr.AudioFile(file_found) as source:
                            audio_data = google_recognizer.record(source)
                            text = google_recognizer.recognize_google(audio_data, language="ru-RU")
                    except sr.UnknownValueError:
                        pass
                    except sr.RequestError:
                        traceback_str = traceback.format_exc()
                        logger.logging(str(traceback_str), Color.RED)

                    # удаление out_all.wav
                    Path(wav_filename).unlink(missing_ok=True)
                    # создание пустого файла
                    AudioSegment.silent(duration=0).export(wav_filename, format="wav")

                    if not text is None:
                        mat_found, text_out = await moderate_mat_in_sentence(text)
                        logger.logging("STT:", text_out, Color.GREEN)
                        if self.with_gpt:
                            chatGPT = ChatGPT()
                            answer = await chatGPT.run_all_gpt(f"{self.user.name}:{text_out}",
                                                               user_id=self.user.id,
                                                               gpt_role=self.user.character.gpt_info)
                            await self.ctx.send(answer)
                        else:
                            self.recognized += text_out

                self.stream_sink.buffer.speaking = False
                await asyncio.sleep(0.75)

    logger.logging("Stop_Recording", Color.GREEN)


async def send_file(ctx, file_path, delete_file=False):
    try:
        await ctx.send(file=discord.File(file_path))
        if delete_file:
            await asyncio.sleep(1.5)
            os.remove(file_path)
    except FileNotFoundError:
        await ctx.send('Файл не найден.')
    except discord.HTTPException as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        await ctx.send(f'Произошла ошибка при отправке файла: {e}.')


class AudioPlayerDiscord:
    def __init__(self, ctx):
        create_new = False
        if ctx.guild.id in audio_players:
            try:
                existing_player = audio_players[self.guild]
                self.__dict__.update(existing_player.__dict__)
            except:
                create_new = True
        else:
            create_new = True

        if create_new:
            audio_players[ctx.guild.id] = self
            self.ctx = ctx
            self.guild = ctx.guild.id
            self.voice_channel = ctx.author.voice.channel if ctx.author.voice else None
            self.voice_client = None
            self.queue = []
            self.isPlaying = False

    async def join_channel(self):
        if self.voice_channel:
            self.voice_client = await self.voice_channel.connect()
        else:
            await self.ctx.send(voiceChannelErrorText)

    async def stop(self):
        if self.isPlaying:
            self.voice_client.stop()
            self.isPlaying = False

    async def play(self, audio_file):
        if not self.isPlaying:
            if not self.voice_client or not self.voice_client.is_connected():
                await self.join_channel()

            audio_source = discord.FFmpegPCMAudio(audio_file)
            self.voice_client.play(audio_source, after=lambda e: self.play_next() if e else None)
            self.isPlaying = True
        else:
            self.queue.append(audio_file)
            # await self.ctx.send(f"{audio_file} добавлен в очередь.")

    def play_next(self):
        if self.queue:
            next_audio = self.queue.pop(0)
            audio_source = discord.FFmpegPCMAudio(next_audio)
            self.voice_client.play(audio_source, after=lambda e: self.play_next() if e else None)
            self.isPlaying = True
        else:
            self.isPlaying = False

    async def skip(self):
        if self.isPlaying:
            self.voice_client.stop()

    async def disconnect(self):
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()
            self.isPlaying = False
            self.queue = []


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore")
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
                if "img1" in args:
                    load_images1 = True
                if "img2" in args:
                    load_images1 = True
                    load_images2 = True
        else:
            # raise error & exit
            logger.logging("Укажите discord_TOKEN", Color.RED)
            exit(-1)

        # == load images ==
        if load_images1:
            import discord_bot_images

            logger.logging("load image model on GPU-0", Color.CYAN)
            image_generators.append(Image_Generator(0))
        if load_images2:
            logger.logging("load image model on GPU-1", Color.CYAN)
            image_generators.append(Image_Generator(1))

        # ==== load bot ====
        logger.logging("====load bot====", Color.CYAN)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start(discord_token))
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), Color.RED)
        logger.logging(f"Произошла ошибка", Color.RED)
