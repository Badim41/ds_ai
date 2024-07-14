import asyncio
import os
import random
import re
import subprocess
import sys
import traceback
import zipfile
from contextlib import asynccontextmanager

from discord_tools.detect_mat import moderate_mat_in_sentence
from discord_tools.logs import Logs, Color
from discord_tools.sql_db import set_get_database_async as set_get_config_all
from discord_tools.timer import Time_Count
from pydub import AudioSegment
from pytube import Playlist

import discord
from discord import Option
from discord.ext import commands
from download_voice_model import download_online_model
from function import Character, Voice_Changer, get_link_to_file
from use_free_cuda import Use_Cuda

try:
    import nest_asyncio

    nest_asyncio.apply()
except:
    pass

recognizers = {}
audio_players = {}
dialogs = {}
characters_all = {}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='\\', intents=intents)
cuda_manager = Use_Cuda()
bark_model = None

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

custom_prompts_files = os.listdir("gpt_history/prompts")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class SQL_Keys:
    AIname = "AIname"
    reload = "reload"
    owner_id = "owner_id"
    delay_record = "delay_record"
    gpt_mode = "gpt_mode"
    voice_keys = "voice_keys"

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
        voice_names = asyncio.run(get_voice_list())
        if character_name in voice_names or True: #TODO FIX IT
            self.character = Character(character_name)
        else:
            self.character = Character(voice_names[0])
        
        self.gpt_mode = asyncio.run(set_get_config_all(self.id, SQL_Keys.gpt_mode))
        self.owner = str(self.id) in asyncio.run(set_get_config_all("Default", SQL_Keys.owner_id)).split(";")

    async def set_user_config(self, key, value=None):
        await set_get_config_all(self.id, key, value)
        logger.logging("Change config", key, value) 
        await self.update_values()

    async def update_values(self):
        self.gpt_mode = await set_get_config_all(self.id, SQL_Keys.gpt_mode)
        character_name = await set_get_config_all(self.id, SQL_Keys.AIname)
        logger.logging("New name", character_name) 
        self.character = Character(character_name)


@bot.event
async def on_ready():
    import torch
    devices = torch.cuda.device_count()
    logger.logging('Status: online', "\ncuda:", devices, color=Color.GREEN)

    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, name=f'AI-covers ({devices})'))

    id = await set_get_config_all("Default", SQL_Keys.reload)

    clear_mode = str(id) == "clear"

    if not id or clear_mode:
        id = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")[0]

    logger.logging("ID:", id, color=Color.GRAY)
    if not id == "True":
        user = await bot.fetch_user(int(id))
        if clear_mode:
            await user.send("Отчищен!")
        else:
            await user.send("Перезагружен!")


@bot.event
async def on_message(message):

    # other users
    if message.author.bot:
        return

    await bot.process_commands(message)


@bot.slash_command(name="help", description='помощь по командам')
async def help_command(
        ctx,
        command: Option(str, description='Нужная вам команда', required=True,
                        choices=['say', 'read_messages', 'ai_cover', 'tts', 'add_voice', 'create_dialog',
                                 'upscale_image', 'generate_video', 'generate_audio', 'generate_image',
                                 'inpaint_image', 'example_image', 'join', 'disconnect', 'record', 'stop_recording',
                                 'pause', 'skip', 'bark']
                        ),
):
    if command == "say":
        await ctx.respond(
            "# /say\n(Сделать запрос к GPT)\n**text - запрос для GPT**\ngpt_mode\*:\n- много ответов / быстрый ответ\n")
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
            "войс-чата)\noutput - link - сслыка на архив, all_files - все "
            "файлы, file - только финальный файл\nonly_voice_change - просто заменить голос, без разделения вокала "
            "и музыки\n")
    elif command == "tts":
        await ctx.respond(
            "# /tts\n(Озвучить текст)\n**text - произносимый текст**\nvoice_name - голосовая модель\nspeed - "
            "Ускорение/замедление\nvoice_model - Модель голоса elevenlab\noutput - Отправляет файл в чат\n"
            "stability - Стабильность голоса (0 - нестабильный, 1 - стабильный)\n"
            "similarity_boost - Повышение сходства (0 - отсутствует)\n"
            "style - Выражение (0 - мало пауз и выражения, 1 - большое количество пауз и выражения)\n")
    elif command == "add_voice":
        text = ("# /add_voice\n(Добавить голосовую модель)\n**url - ссылка на модель **\n**name - имя модели "
                "**\n**gender - пол модели (для тональности)**\ninfo - информация о человеке (для запроса GPT)\n"
                "speed - ускорение/замедление при /tts\nvoice_model - модель elevenlab\nchange_voice - True = "
                "заменить на текущий голос\ntxt_file - быстрое добавление множества голосовых моделей *(остальные аргументы как 'url', 'gender', 'name'  будут игнорироваться)*, для использования:\n"
                "- напишите в txt файле аргументы для add_voice (1 модель - 1 строка), пример:")
        await send_file(ctx, "add_voice_args.txt", text=text)
    elif command == "create_dialog":
        await ctx.respond(
            "# /create_dialog\n(Создать диалог в войс-чате)\n**names - участники диалога "
            "через ';' - список голосовых моделей Например, Участник1;Участник2**\ntheme - Тема разговора "
            "(может измениться)\nprompt - Постоянный запрос (например, что они находятся в определённом месте)\n")
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
    elif command == "bark":
        await ctx.respond(
            "# /bark\nИспользуется для создания аудио на основе текста с использованием модели генерации речи.\n"
            "**text** - Текст, который будет преобразован в речь.\n"
            "speaker - Модель голоса (1)\n"
            "gen_temp - Температура генерации (0.6)")
    elif command == "upscale_image":
        await ctx.respond(
            "# /upscale_image\n(Увеличить масштаб изображения с помощью нейросети)\n**image - изображение**\n**prompt - запрос (что изображено на картинке)**\nsteps - количество шагов для генерации (75)\n")
    elif command == "generate_video":
        await ctx.respond(
            "# /generate_video\n(Создать видео на основе изображения с помощью нейросети)\n**image - изображение (None)**\n**prompt - запрос для начального изображения (None)**\nfps - количество кадров в секунду (20)\nsteps - количество шагов для генерации. Чем больше, тем дольше генерация (25)\nseed - сид генератора (random)\nduration - длительность видео (2)\ndecode_chunk_size - декодирование кадров за раз. Влияет на использование видеопамяти (1)\nnoise_strenght - количество добавляемого шума к исходному изображению (0.02)\nrepeats - количество повторов (1)\n")
    elif command == "generate_audio":
        await ctx.respond(
            "# /generate_audio\n(Создать аудиофайл с помощью нейросети)\n**prompt - запрос**\n**duration - длительность аудио в секундах**\nsteps - количество шагов для генерации (200)\nseed - сид (random)\nrepeats - количество повторов (1)\n")
    elif command == "generate_image":
        await ctx.respond(
            "# /generate_image\n(Создать изображение нейросетью)\n**prompt - запрос**\n**negative_prompt - негативный запрос (None)**\nx - размер картинки по x (1024)\ny - размер картинки по y (1024)\nstyle - стиль (DEFAULT)\nrepeats - количество повторов (1)\napi - True - Kandinsky 3 API; False - Stable Diffusion XL\nsteps - число шагов. Чем больше, тем дольше генерация  (50)\nseed - сид (random)\nrefine - улучить изображение (False)\n")
    elif command == "inpaint_image":
        await ctx.respond(
            "# /inpaint_image\n(Изменить изображение нейросетью)\n**image - изображение**\n**prompt - запрос**\nmask - маска. Будут изменены только БЕЛЫЕ пиксели (All)\ninvert - изменить всё, КРОМЕ белых пикселей (False)\nnegative_prompt - негативный запрос (None)\nsteps - число шагов. Чем больше, тем дольше генерация  (50)\nstrength - насколько сильны будут изменения (0.5)\nseed - сид (random)\nrepeats - количество повторов (1)\nconsistently - увеличивать изменение картинки последовательно (False)\nrefine - улучить изображение (False)\n")
    elif command == "example_image":
        await ctx.respond(
            "# /example_image\n(Изменить изображение нейросетью с помощью примера)\n**image - изображение**\n**example - изображение**\nmask - маска. Будут изменены только БЕЛЫЕ пиксели (All)\ninvert - изменить всё, КРОМЕ белых пикселей (False)\nsteps - число шагов. Чем больше, тем дольше генерация  (50)\nseed - Сид (random)\nrepeats - количество повторов (1)\n")


@bot.slash_command(name="config", description='изменить конфиг')
@discord.default_permissions(
    administrator=True
)
async def __config(
        ctx,
        section: Option(str, description='секция', required=True),
        key: Option(str, description='ключ', required=True),
        value: Option(str, description='значение', required=False, default=None)
):
    try:
        await ctx.defer()
        owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
        if str(ctx.author.id) not in owner_ids:
            await ctx.author.send("Доступ запрещён")
            return
        result = await set_get_config_all(section, key, value)
        if value is None:
            await ctx.respond(result)
        else:
            await ctx.respond(section + " " + key + " " + value)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Ошибка при изменении конфига (с параметрами{section},{key},{value}): {e}")


@bot.slash_command(name="join", description='присоединиться к голосовому каналу')
async def join(ctx):
    await ctx.defer()
    await AudioPlayerDiscord(ctx).join_channel()
    await ctx.respond("Присоединяюсь")


@bot.slash_command(name="disconnect", description='выйти из войс-чата')
async def disconnect(ctx):
    await ctx.defer()

    # остановка записи
    author_id = ctx.author.id
    if author_id in recognizers:
        recognizer = recognizers[author_id]
        if recognizer:
            await recognizer.stop_recording()

    await AudioPlayerDiscord(ctx).disconnect()
    await ctx.respond("Покидаю войс-чат")


@bot.slash_command(name="pause", description='пауза/воспроизведение (остановка диалога)')
async def pause(ctx):
    await ctx.defer()
    guild_id = ctx.guild.id
    if guild_id in dialogs:
        dialog = dialogs[guild_id]
        if dialog:
            await dialog.stop_dialog()
            await ctx.respond("Остановлен диалог")
            return
    result = await AudioPlayerDiscord(ctx).stop()
    await ctx.respond(result)


@bot.slash_command(name="skip", description='пропуск аудио')
async def skip(ctx):
    await ctx.defer()
    result = await AudioPlayerDiscord(ctx).skip()
    await ctx.respond(result)


async def get_voice_list():
    from cover_gen import rvc_models_dir
    directory_path = rvc_models_dir

    # Получение имен папок
    return [folder for folder in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, folder))]


@bot.slash_command(name="tts", description='Заставить бота говорить всё, что захочешь')
async def __tts(
        ctx,
        text: Option(str, description='Текст для озвучки', required=True),
        voice_names: Option(str, description='Голоса для озвучки через ; (User character)', required=False,
                            default=None),
        speed: Option(float, description='Ускорение голоса (Character)', required=False, default=None, min_value=1,
                      max_value=3),
        voice_model_eleven: Option(str, description=f'Какая модель elevenlabs будет использована (Character)',
                                   required=False,
                                   default=None),
        stability: Option(float, description='Стабильность голоса (Character)', required=False, default=None,
                          min_value=0,
                          max_value=1),
        similarity_boost: Option(float, description='Повышение сходства (Character)', required=False, default=None,
                                 min_value=0,
                                 max_value=1),
        style: Option(float, description='Выражение (Character)', required=False, default=None, min_value=0,
                      max_value=1),
        output: Option(str, description='Отправить результат (1 файл RVC)', required=False,
                       choices=["1 файл (RVC)", "2 файла (RVC & elevenlabs/GTTS)", "None"], default="1 файл (RVC)"),
        pitch: Option(int, description="Изменить тональность (Character)", required=False, default=0, min_value=-24,
                      max_value=24),
        palgo: Option(str, description='Алгоритм. Rmvpe - лучший вариант, mangio-crepe - более мягкий вокал (rmvpe)',
                      required=False,
                      choices=['rmvpe', 'mangio-crepe'], default="rmvpe"),

):
    await ctx.defer()
    user = DiscordUser(ctx)

    if not voice_names:
        voice_names = [user.character.name]
    else:
        voice_names = voice_names.split(";")

    mat_found, text = await moderate_mat_in_sentence(text)
    if mat_found and False:
        await ctx.respond("Такое точно нельзя произносить!")
        return

    voices = await get_voice_list()
    for voice_name in voice_names:
        if str(voice_name) not in voices:
            return await ctx.respond("Выберите голос для озвучки (или /add_voice): " + ';'.join(voices))

        if not user.character.name == voice_name:
            await ctx.send("Обновлена базовая модель на:" + voice_name)
            await user.set_user_config(SQL_Keys.AIname, voice_name)

        if voice_model_eleven == "All":
            voice_models = ALL_VOICES.keys()
        else:
            if voice_model_eleven is None:
                voice_model_eleven = user.character.voice_model_eleven
                if voice_model_eleven is None:
                    return await ctx.respond(
                        f"Голосовая модель персонажа: {voice_model_eleven}, что недопустимо")
            if voice_model_eleven not in ALL_VOICES.keys():
                await ctx.respond("Список голосов elevenlabs: \n" + ';'.join(ALL_VOICES.keys()))
                return
            voice_models = [voice_model_eleven]
        character = user.character

        try:
            # cuda_number = await cuda_manager.use_cuda()
            await character.load_voice(0, speed=speed, stability=stability, similarity_boost=similarity_boost,
                                       style=style, pitch=pitch, algo=palgo)
            for voice_model in voice_models:
                audio_path_1 = f"{user.id}-{voice_model}-tts-row.mp3"
                audio_path_2 = f"{user.id}-{voice_model}-tts.mp3"
                timer = Time_Count()
                character.voice.voice_model_eleven = voice_model
                # logger.logging("text to speech temp-3", text, color=Color.GRAY)
                mat_found, text = await moderate_mat_in_sentence(text)
                # logger.logging("text to speech temp-2", text, color=Color.GRAY)
                if mat_found:
                    await ctx.respond("Такое точно нельзя произносить!")
                    return
                # запускаем TTS
                await character.text_to_speech(text, audio_path=audio_path_1, output_name=audio_path_2)
                # перестаём использовать видеокарту

                spent_time = f"({voice_name})\nПотрачено на обработку:" + timer.count_time()
                if output:
                    if output.startswith("1"):
                        await send_file(ctx, audio_path_2, text=spent_time)
                    elif output.startswith("2"):
                        await send_file(ctx, audio_path_1, text=spent_time)
                        await send_file(ctx, audio_path_2)

                os.remove(audio_path_1)
                os.remove(audio_path_2)
            # await cuda_manager.stop_use_cuda(cuda_number)
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.logging(str(traceback_str), color=Color.RED)
            await ctx.respond(f"Ошибка при озвучивании текста (с параметрами {text}): {e}")
            # перестаём использовать видеокарту
            # await cuda_manager.stop_use_cuda(CUDA_NUMBER) 

async def send_output(ctx, audio_path, output, timer):
    text = "===Файлы " + os.path.basename(audio_path)[:-4] + "==="
    output = output.replace(" ", "")
    # конечный файл
    if output == "file":
        await send_file(ctx, audio_path, text=text)
    # все файлы
    elif output == "all_files":
        for filename in os.listdir(os.path.dirname(audio_path)):
            file_path = os.path.join(os.path.dirname(audio_path), filename)
            await send_file(ctx, file_path, text=f"{text}+\n{filename}")
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
    logger.logging("Играет " + os.path.basename(audio_path)[:-4], color=Color.GREEN)
    audio_player = AudioPlayerDiscord(ctx)
    await audio_player.play(audio_path, is_send_file=False)

    if not output == "None":
        await ctx.send(timer.count_time())

    else:
        await ctx.send("Произошла ошибка")


async def run_ai_cover_gen_several_cuda(song_input, rvc_dirname, pitch, index_rate, filter_radius, rms_mix_rate,
                                        protect, pitch_detection_algo,
                                        crepe_hop_length, main_vol, backup_vol,
                                        inst_vol, reverb_size, reverb_wetness, reverb_dryness,
                                        reverb_damping,
                                        output_format, output, ctx, change_back_vocal):
    try:
        from cover_gen import run_ai_cover_gen
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
                                            output_format=output_format, cuda_number=cuda_number, change_back_vocal=change_back_vocal)
        await send_output(ctx=ctx, audio_path=audio_path, output=output, timer=timer)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Ошибка при изменении голоса(ID:d5): {e}")

    await cuda_manager.stop_use_cuda(cuda_number)


@bot.slash_command(name="ai_cover", description='Заставить бота озвучить видео/спеть песню')
async def __cover(
        ctx,
        url: Option(str, description='Ссылка на видео', required=False, default=None),
        audio_path: Option(discord.SlashCommandOptionType.attachment, description='Аудиофайл',
                           required=False, default=None),
        voice_names: Option(str, description='Голоса для озвучки через ;', required=False, default=None),
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
        hop: Option(int, description='Как часто проверяет изменения тона в mango-crepe', required=False, default=None,
                    min_value=64,
                    max_value=1280),
        output: Option(str, description='Отправить результат',
                       choices=["ссылка на все файлы", "только результат (1 файл)", "все файлы", "не отправлять"],
                       required=False, default="только результат (1 файл)"),
        only_voice_change: Option(bool,
                                  description='Не извлекать инструментал и бэквокал, изменить голос. Не поддерживаются ссылки',
                                  required=False, default=False),

        change_back_vocal: Option(bool, description='Изменить голос в бэквакале (False)',
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
            logger.logging(str(traceback_str), color=Color.RED)
            logger.logging(f"Произошла ошибка при извлечении плейлиста", color=Color.RED)
            return []

    palgo = 'mangio-crepe' if hop else 'rmvpe'

    output = output.replace("ссылка на все файлы", "link").replace("только результат (1 файл)", "file").replace(
        "все файлы", "all_files").replace("не отправлять", "None")
    try:
        await ctx.defer()
        user = DiscordUser(ctx)

        if not voice_names:
            voice_names = [user.character.name]
        else:
            voice_names = voice_names.split(";")

        voices = await get_voice_list()
        for voice_name in voice_names:
            if voice_name not in voices:
                await ctx.respond("Выберите голос для озвучки (или /add_voice):" + ', '.join(voices))
                return

            
            if not user.character.name == voice_name:
                await ctx.send("Обновлена базовая модель на:" + voice_name)
                await user.set_user_config(SQL_Keys.AIname, voice_name)
            
            if pitch is None:
                pitch = user.character.pitch

            logger.logging("suc params", color=Color.CYAN)

            urls = []
            if audio_path:
                print("Audio path.")
                timer = Time_Count()
                filename = f"{ctx.author.id}-{random.randint(1, 1000000)}.mp3"
                await audio_path.save(filename)
                print("Audio path saved.")
                urls.append(filename)
                if only_voice_change:
                    cuda_number = await cuda_manager.use_cuda()
                    voice_changer = Voice_Changer(cuda_number=cuda_number, voice_name=voice_name, index_rate=indexrate,
                                                  pitch=pitch, filter_radius=filter_radius, rms_mix_rate=rms_mix_rate,
                                                  protect=0.3, algo=palgo, hop=hop)
                    await voice_changer.voice_change(input_path=filename, output_path=filename)
                    text = f"({voice_name})\nПотрачено:{timer.count_time()}"
                    await send_file(ctx, file_path=filename, text=text)
                    await cuda_manager.stop_use_cuda(cuda_number)
                    continue
            elif url:
                if ";" in url:
                    urls += url.split(";")
                elif "playlist" in url:
                    urls += (await get_links_from_playlist(url)).split(";")
                else:
                    urls.append(url)

            for i, url in enumerate(urls):
                asyncio.create_task(
                    run_ai_cover_gen_several_cuda(song_input=url, rvc_dirname=voice_name, pitch=pitch,
                                                  index_rate=indexrate,
                                                  filter_radius=filter_radius, rms_mix_rate=rms_mix_rate, protect=0.3,
                                                  pitch_detection_algo=palgo,
                                                  crepe_hop_length=hop, main_vol=main_vocal, backup_vol=back_vocal,
                                                  inst_vol=music, reverb_size=roomsize, reverb_wetness=wetness,
                                                  reverb_dryness=dryness,
                                                  reverb_damping=0.7,
                                                  output_format='mp3', output=output, ctx=ctx, change_back_vocal=change_back_vocal))
            if not urls:
                await ctx.respond('Не указана ссылка или аудиофайл')
                return

            if not user.character.name == voice_names[0]:
                await ctx.send("Обновлена базовая модель на:" + voice_names[0])
                await user.set_user_config(SQL_Keys.AIname, voice_names[0])

    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Ошибка при изменении голоса(ID:d5): {e}")
        await cuda_manager.stop_use_cuda(cuda_number)


@bot.slash_command(name="add_voice", description='Добавить RVC голос')
async def __add_voice(
        ctx,
        url: Option(str, description='Ссылка на .zip файл с моделью RVC', required=True),
        name: Option(str, description=f'Имя модели', required=True),
        gender: Option(str, description=f'Пол (pitch)', required=False,
                       choices=['мужчина', 'женщина']),
        pitch: Option(int, description="Тональность. Мужчина=0, женщина=12 (gender/0)",
                      required=False, default=0, min_value=-24, max_value=24),
        info: Option(str, description=f'Какие-то сведения о данном человеке (Отсутствует)', required=False,
                     default="Отсутствует"),
        speed: Option(float, description=f'Ускорение/замедление голоса (1)', required=False,
                      default=1, min_value=1, max_value=3),
        voice_model_eleven: Option(str, description=f'Какая модель elevenlabs будет использована (Adam)',
                                   required=False,
                                   default="Adam"),
        change_voice: Option(bool, description=f'Изменить голос на этот (False)', required=False,
                             default=False),
        txt_file: Option(discord.SlashCommandOptionType.attachment,
                         description='Файл txt для добавления нескольких моделей сразу (None)',
                         required=False, default=None)
):
    if voice_model_eleven not in ALL_VOICES.keys():
        await ctx.respond("Список голосов: \n" + '; '.join(ALL_VOICES.keys()))
        return
    await ctx.defer()

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
        await ctx.respond("Все модели успешно установлены!")
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
    except:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        return None, None, None, None, None, None, None, None, None


async def download_voice(ctx, url, name, gender, info, speed, voice_model_eleven, change_voice, stability="0.4",
                         similarity_boost="0.25", style="0.4"):
    if name == "None" or ";" in name or "/" in name or "\\" in name:
        await ctx.respond('Имя не должно содержать \";\" \"/\" \"\\\" или быть None')

    name = name.replace(" ", "_")
    if gender == "женщина":
        gender = "female"
    elif gender == "мужчина":
        gender = "male"
    else:
        gender = str(gender)
    try:
        parameters = {
            "info": info,
            "gender": gender.replace(" ", ""),
            "speed": str(speed).replace(" ", ""),
            "voice_model_eleven": voice_model_eleven,
            "stability": stability.replace(" ", ""),
            "similarity_boost": similarity_boost.replace(" ", ""),
            "style": style.replace(" ", ""),
        }
        success, result = await download_online_model(url=url, dir_name=name, parameters=parameters)

        if change_voice and success:
            user = DiscordUser(ctx)
            await user.set_user_config(SQL_Keys.AIname, name)
        await ctx.send(result)

        # Удаляем модель, если она существует
        if name in characters_all:
            del characters_all[name]

    except subprocess.CalledProcessError as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond("Ошибка при скачивании голоса.")


async def command_line(ctx, command):
    logger.logging("command line:", command)
    text = "."
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        for line in stdout.decode().split('\n'):
            if line.strip():
                text += line + "\n"
        for line in stderr.decode().split('\n'):
            if line.strip():
                text += line + "\n"
    except subprocess.CalledProcessError as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.author.send(f"Ошибка выполнения команды: {e}")
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.author.send(f"Произошла неизвестная ошибка: {e}")
    await ctx.author.send(text[:1900])


@bot.command(aliases=['cmd'], help="командная строка")
async def commands(ctx, *args):
    owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
    if str(ctx.author.id) not in owner_ids:
        await ctx.author.send("Доступ запрещён")
        return

    # Получение объекта пользователя по ID
    command = " ".join(args)
    asyncio.create_task(command_line(ctx=ctx, command=command))


@bot.command(aliases=['send'], help="Отправить файл")
async def send_smth(ctx, *args):
    owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
    if str(ctx.author.id) not in owner_ids:
        await ctx.author.send("Доступ запрещён")
        return
    file_path = ''.join(args)
    await send_file(ctx=ctx, file_path=file_path, text=file_path)


@bot.command(aliases=['restart'], help="Перезагрузка")
async def command_restart(ctx):
    owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
    if str(ctx.author.id) not in owner_ids:
        await ctx.author.send("Доступ запрещён")
        return
    await ctx.send("Перезагрузка")
    await set_get_config_all("Default", SQL_Keys.reload, ctx.author.id)

    for id, audio_player in audio_players.items():
        try:
            await audio_player.disconnect()
        except Exception as e:
            print("CANT LEAVE VOICE:", e)
    os.kill(os.getpid(), 9)


@bot.command(aliases=['exit'], help="Выключиться")
async def command_exit(ctx, *args):
    owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
    if str(ctx.author.id) not in owner_ids:
        await ctx.author.send("Доступ запрещён")
        return
    time = ''.join(args).replace(" ", "")
    if time:
        await ctx.send(f"Выключение через {time} секунд")
        await asyncio.sleep(int(time))
    else:
        await ctx.send(f"Выключение")
    await set_get_config_all("Default", SQL_Keys.reload, "False")

    for id, audio_player in audio_players.items():
        try:
            await audio_player.disconnect()
        except Exception as e:
            print("CANT LEAVE VOICE:", e)
    os.kill(os.getpid(), 9)


@bot.command(aliases=['clear'], help="Отчистить память")
async def command_clear(ctx):
    owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
    if str(ctx.author.id) not in owner_ids:
        await ctx.author.send("Доступ запрещён")
        return
    await set_get_config_all("Default", SQL_Keys.reload, "clear")
    os.kill(os.getpid(), 9)


@bot.command(aliases=['log'], help="логи")
async def command_log(ctx):
    owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
    if str(ctx.author.id) not in owner_ids:
        await ctx.author.send("Доступ запрещён")
        return

    logs_path = "__logs__"
    if os.path.exists(logs_path):
        with open(logs_path, "r", encoding="utf-8") as file:
            content = file.read()[-1990:]
            await ctx.send(content)
    else:
        await ctx.send("Логов нет. Странно, не правда?")



async def send_file(ctx, file_path, delete_file=False, text=""):
    try:
        try:
            await ctx.respond(content=text, file=discord.File(file_path))
        except:
            await ctx.send(content=text, file=discord.File(file_path))
        if delete_file:
            await asyncio.sleep(1.5)
            os.remove(file_path)
    except FileNotFoundError:
        await ctx.send('Файл не найден.')
    except discord.HTTPException as e:
        traceback_str = traceback.format_exc()
        logger.logging("ERROR SEND FILE:", str(traceback_str), color=Color.RED)
        await ctx.send(f'Произошла ошибка при отправке файла: {e}.')


async def send_lm(user_id, text):
    try:
        print("USER_ID:", user_id)
        user = await bot.fetch_user(int(user_id))
        await user.send(text)
    except discord.HTTPException as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)


@asynccontextmanager
async def audio_play_lock():
    lock = asyncio.Lock()
    async with lock:
        yield lock


class AudioPlayerDiscord:
    def __init__(self, ctx):
        self.guild = ctx.guild
        self.ctx = ctx
        if self.guild:
            create_new = False
            if ctx.guild.id in audio_players:
                try:
                    existing_player = audio_players[ctx.guild.id]
                    self.__dict__.update(existing_player.__dict__)
                    self.voice_channel = ctx.author.voice.channel if ctx.author.voice else None
                except:
                    create_new = True
            else:
                create_new = True

            if create_new:
                logger.logging("Новый audio_player", color=Color.PURPLE)
                audio_players[ctx.guild.id] = self
                self.ctx = ctx
                self.guild = ctx.guild.id
                self.voice_channel = ctx.author.voice.channel if ctx.author.voice else None
                self.voice_client = None
                self.queue = []
                self.play_event = asyncio.Event()
                self.isPlaying = False
                self.paused = False

    async def join_channel(self):
        if self.guild:
            ctx = self.ctx
            try:
                if self.voice_client is None:
                    if ctx.author.voice:
                        self.voice_client = await ctx.author.voice.channel.connect()
                        return self.voice_client
                await ctx.send(voiceChannelErrorText)
            except discord.ClientException as e:
                logger.logging("Уже в голосовом канале", e, color=Color.GRAY)
                self.voice_client = await ctx.voice_client.move_to(self.voice_channel)
                return self.voice_client

    async def stop(self):
        if self.guild:
            if self.paused:
                self.paused = False
                return "Воспроизведение"
            if self.isPlaying:
                self.paused = True
                self.voice_client.stop()
                return "Остановлено"
            else:
                return "Нет аудио для остановки"
        else:
            return "Вы не на сервере"

    async def play(self, audio_file, delete_file=False, is_send_file=True):
        if not self.guild:
            if is_send_file:
                await send_file(self.ctx, audio_file, text="Невозможно проиграть файл")
            return

        async with audio_play_lock():
            self.isPlaying = True
            if not self.voice_client or not self.voice_client.is_connected():
                await self.join_channel()
            try:
                audio_source = discord.FFmpegPCMAudio(audio_file)
                audio_duration = AudioSegment.from_file(audio_file).duration_seconds
                self.voice_client.play(audio_source)
                await asyncio.sleep(audio_duration)

                # Пауза
                while self.paused:
                    logger.logging("На паузе", color=Color.GRAY)
                    await asyncio.sleep(0.25)

                if delete_file:
                    os.remove(audio_file)
                self.isPlaying = False
                logger.logging("Finished play", color=Color.GRAY)
            except discord.ClientException:
                logger.logging("already playing smth, not wait", color=Color.RED)

    async def skip(self):
        if self.isPlaying:
            self.voice_client.stop()
            return "Пропущено"
        else:
            return "Нет аудио для пропуска"

    async def disconnect(self):
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect(force=True)
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
        else:
            # raise error & exit
            logger.logging("Укажите discord_TOKEN", color=Color.RED)
            exit(-1)

        # ==== load bot ====
        logger.logging("====load Bot 2====", color=Color.CYAN)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start(discord_token))
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        logger.logging(f"Произошла ошибка", color=Color.RED)
