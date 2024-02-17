import asyncio
import os
import random
import re
import subprocess
import sys
import traceback
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path
from pydub import AudioSegment
from pytube import Playlist

import speech_recognition as sr

import discord
from bark_tts import BarkTTS
from discord import Option
from discord.ext import commands
from discord_tools.chat_gpt import ChatGPT
from discord_tools.detect_mat import moderate_mat_in_sentence
from discord_tools.logs import Logs, Color
from discord_tools.sql_db import set_get_database_async as set_get_config_all
from discord_tools.timer import Time_Count
from download_voice_model import download_online_model
from function import Character, Voice_Changer, get_link_to_file, upscale_image, \
    generate_audio, generate_video, inpaint_image, generate_image_API, generate_image_with_example, generate_image_sd
from modifed_sinks import StreamSink
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
        self.character = Character(character_name)
        self.gpt_mode = asyncio.run(set_get_config_all(self.id, SQL_Keys.gpt_mode))
        self.owner = str(self.id) in asyncio.run(set_get_config_all("Default", SQL_Keys.owner_id)).split(";")

    async def set_user_config(self, key, value=None):
        await set_get_config_all(self.id, key, value)
        await self.update_values()

    async def update_values(self):
        self.gpt_mode = await set_get_config_all(self.id, SQL_Keys.gpt_mode)
        character_name = await set_get_config_all(self.id, SQL_Keys.AIname)
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
    ctx = await bot.get_context(message)
    if message.author.id == 1165023027847757836:  # minecraft chat bot
        text = message.content
        if text.startswith("\\themer "):
            text = text.replace("\\themer ", "")

            guild_id = ctx.guild.id
            if guild_id in dialogs:
                dialog = dialogs[guild_id]
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
                audio_path_1 = f"{user.id}-{user.character.name}-message-row.mp3"
                audio_path_2 = f"{user.id}-{user.character.name}-message.mp3"
                await user.character.text_to_speech(answer, audio_path=audio_path_1, output_name=audio_path_2)
                await audio_player.play(audio_path_2)

                os.remove(audio_path_1)
                os.remove(audio_path_2)
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.logging(str(traceback_str), color=Color.RED)
            await ctx.send(f"Ошибка при команде say с параметрами {message}: {e}")
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
        await ctx.respond("# /add_voice\n(Добавить голосовую модель)\n**url - ссылка на модель **\n**name - имя модели "
                          "**\n**gender - пол модели (для тональности)**\ninfo - информация о человеке (для запроса GPT)\n"
                          "speed - ускорение/замедление при /tts\nvoice_model - модель elevenlab\nchange_voice - True = "
                          "заменить на текущий голос\ntxt_file - быстрое добавление множества голосовых моделей *(остальные аргументы как 'url', 'gender', 'name'  будут игнорироваться)*, для использования:\n"
                          "- напишите в txt файле аргументы для add_voice (1 модель - 1 строка), пример:")
        await send_file(ctx, "add_voice_args.txt")
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


@bot.slash_command(name="upscale_image", description='Увеличить масштаб изображения с помощью нейросети')
async def __upscale_image_command(ctx,
                                  image: Option(discord.SlashCommandOptionType.attachment, description='Изображение',
                                                required=True),
                                  prompt: Option(str, description='Запрос (что изображено на картинке)', required=True),
                                  steps: Option(int, description='Количество шагов для генерации (75)', required=False,
                                                default=75, min_value=1, max_value=150)
                                  ):
    try:
        await ctx.defer()
        image_path = "images/image" + str(ctx.author.id) + "_upscale.png"
        await image.save(image_path)

        cuda_number = await cuda_manager.use_cuda()
        timer = Time_Count()

        await asyncio.to_thread(
            upscale_image, cuda_number=cuda_number, image_path=image_path, prompt=prompt, steps=steps
        )

        await ctx.respond(f"Изображение успешно увеличено!\nПотрачено: {timer.count_time()}")
        await send_file(ctx, image_path)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Ошибка:{e}")
    finally:
        await cuda_manager.stop_use_cuda(cuda_number)


async def image_prompt_with_gpt(prompt, iteration=0):
    if iteration == 3:
        return prompt

    with open(f"gpt_history/prompts/image") as file:
        content = file.read()
    result = await ChatGPT().run_all_gpt(content + prompt)
    if not result == "" and "fulfill that request" not in result and not "I'm sorry" in result:
        if "```" in result:
            result = result[result.find("```") + 3:]
            result = result[:result.find("```")]
        if "Example 5:" in result:
            result = result[result.find("Example 5:") + 10:]
        if "description:" in result:
            result = result[result.find("description:") + 12:]
        if "Example:" in result:
            result = result[result.find("Example:") + 8:]
        return result
    else:
        result = await image_prompt_with_gpt(prompt, iteration=iteration+1)
        return result


@bot.slash_command(name="generate_video", description='Создать видео на основе изображения с помощью нейросети')
async def __generate_video(ctx,
                           image: Option(discord.SlashCommandOptionType.attachment, description='Изображение (None)',
                                         required=False),
                           prompt: Option(str, description="Запрос для начального изображения (None)", required=False,
                                          default=None),
                           fps: Option(int, description='Количество кадров в секунду (20)', required=False,
                                       default=20),
                           steps: Option(int, description='Количество шагов для генерации (25)', required=False,
                                         default=25,
                                         min_value=1, max_value=100),
                           seed: Option(int, description='Сид генератора (random)', required=False, default=None,
                                        min_value=9999999999, max_value=9999999999),
                           duration: Option(int, description='Длительность видео (2)', required=False, default=2),
                           decode_chunk_size: Option(int,
                                                     description='Декодирование кадров за раз. Влияет на использование видеопамяти (1)',
                                                     required=False, default=1),
                           noise_strenght: Option(float,
                                                  description='Количество добавляемого шума к исходному изображению (0.02)',
                                                  required=False, default=0.02),
                           repeats: Option(int,
                                           description='Количество повторов (1)',
                                           required=False,
                                           default=1, min_value=1,
                                           max_value=4),
                           gpt: Option(bool, description="Улучить запрос с помощью ChatGPT (False)", required=False,
                                       default=False)
                           ):
    async def repeat_generate_videos(seed, i):
        try:
            seed = random.randint(1, 9999999999) if seed is None else seed // (i + 1)

            cuda_number = await cuda_manager.use_cuda()

            timer = Time_Count()

            image_path = f"images/{ctx.author.id}_generate_video{i}.png"
            if image:
                if prompt:
                    await ctx.send("Загружено изображение, prompt игнорируется")
                await image.save(image_path)
            else:
                if not prompt:
                    await ctx.respond("Загрузите изображение или напишите запрос (prompt)")
                    return

                try:
                    image_path = f"images/image{ctx.author.id}_{seed}_generate_API.png"
                    await asyncio.to_thread(
                        generate_image_API, prompt=prompt, x=1024, y=720, negative_prompt=".", style="DEFAULT",
                        image_path=image_path
                    )
                except Exception as e:
                    logger.logging("Cant generate image", e, color=Color.GRAY)
                    image_path = f"images/image{ctx.author.id}_{seed}_generate_sd.png"
                    await asyncio.to_thread(
                        generate_image_sd, image_path=image_path, prompt=prompt, x=1280, y=720,
                        steps=steps, seed=seed, cuda_number=cuda_number, negative_prompt=".", refine=False
                    )

            video_path, gif_path = await asyncio.to_thread(
                generate_video, cuda_number=cuda_number, image_path=image_path, seed=seed, fps=fps,
                decode_chunk_size=decode_chunk_size, duration=duration, steps=steps,
                noise_strenght=noise_strenght
            )

            await ctx.respond(f"Видео: {i + 1}/{repeats}\nПотрачено:{timer.count_time()}\nСид:{seed}")
            await send_file(ctx, video_path)
            await send_file(ctx, gif_path)
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.logging(str(traceback_str), color=Color.RED)
            await ctx.respond(f"Ошибка:{e}")
        finally:
            await cuda_manager.stop_use_cuda(cuda_number)

    if not image and prompt and gpt:
        prompt = await image_prompt_with_gpt(prompt)
        await ctx.send(f"Запрос:\n{prompt}")

    await ctx.defer()
    for i in range(repeats):
        asyncio.create_task(repeat_generate_videos(seed, i))


@bot.slash_command(name="generate_audio", description='Создать аудиофайл с помощью нейросети')
async def __generate_audio(ctx,
                           prompt: Option(str, description='Запрос', required=True),
                           duration: Option(float, description='Длительность аудио в секундах', required=True),
                           steps: Option(int, description='Количество шагов для генерации (200)', required=False,
                                         default=200,
                                         min_value=1, max_value=1000),
                           seed: Option(int,
                                        description='Сид (random)',
                                        required=False,
                                        default=None, min_value=1,
                                        max_value=9999999999),
                           repeats: Option(int,
                                           description='Количество повторов (1)',
                                           required=False,
                                           default=1, min_value=1,
                                           max_value=16),
                           gpt: Option(bool, description="Улучить запрос с помощью ChatGPT (False)", required=False,
                                       default=False)
                           ):
    async def generate_audios_async(seed, i):
        try:
            seed = random.randint(1, 9999999999) if seed is None else seed // (i + 1)

            cuda_number = await cuda_manager.use_cuda()
            timer = Time_Count()
            wav_audio_path = f"{ctx.author.id}_generate_audio{i}.wav"
            await asyncio.to_thread(
                generate_audio, cuda_number=cuda_number, wav_audio_path=wav_audio_path, prompt=prompt,
                duration=duration,
                steps=steps, seed=seed
            )

            await ctx.respond(
                f"Аудиофайл {i + 1}/{repeats}\nЗапрос:{prompt}\nСид:{seed}\nПотрачено: {timer.count_time()}")
            await send_file(ctx, wav_audio_path, delete_file=True)
        except Exception as e:
            await ctx.respond(f"Ошибка:{e}")
            traceback_str = traceback.format_exc()
            logger.logging(str(traceback_str), color=Color.RED)
        finally:
            await cuda_manager.stop_use_cuda(cuda_number)

    if gpt:
        with open(f"gpt_history/prompts/music") as file:
            content = file.read()
        prompt = await ChatGPT().run_all_gpt(content + prompt)

    await ctx.defer()
    for i in range(repeats):
        asyncio.create_task(generate_audios_async(seed, i))


@bot.slash_command(name="generate_image", description='создать изображение нейросетью')
async def __generate_image(ctx,
                           prompt: Option(str, description='Запрос', required=True),
                           negative_prompt: Option(str, description='Негативный запрос (None)', default=".",
                                                   required=False),
                           x: Option(int,
                                     description='Размер картинки по x (1024)',
                                     required=False,
                                     default=1024, min_value=64),
                           y: Option(int,
                                     description='Размер картинки по y (1024)',
                                     required=False,
                                     default=1024, min_value=64),
                           style: Option(str, description="Стиль (DEFAULT)", required=False,
                                         choices=["KANDINSKY", "UHD", "ANIME", "DEFAULT"], default="DEFAULT"),
                           repeats: Option(int,
                                           description='Количество повторов (1)',
                                           required=False,
                                           default=1, min_value=1,
                                           max_value=16),
                           api: Option(bool, description="True - Kandinsky 3 API; False - Stable Diffusion XL",
                                       required=False, default=True),
                           steps: Option(int, description='число шагов (50)', required=False,
                                         default=50,
                                         min_value=1,
                                         max_value=100),
                           seed: Option(int,
                                        description='Сид (random)',
                                        required=False,
                                        default=None, min_value=1,
                                        max_value=9999999999),
                           refine: Option(bool, description="Улучить изображение (False)", required=False,
                                          default=False),
                           gpt: Option(bool, description="Улучить запрос с помощью ChatGPT (False)", required=False,
                                       default=False)
                           ):
    async def repeat_generate_images(seed, i):
        try:
            timer = Time_Count()
            seed_text = ""
            if api:
                image_path = f"images/image{ctx.author.id}_{seed}_{i}_generate_API.png"
                await asyncio.to_thread(
                    generate_image_API, prompt=prompt, negative_prompt=negative_prompt,
                    style=style, x=x, y=y, image_path=image_path
                )
            else:
                image_path = f"images/image{ctx.author.id}_{seed}_{i}_generate_sd.png"
                seed = random.randint(1, 9999999999) if seed is None else seed // (i + 1)
                seed_text = f"\nСид:{seed}"
                cuda_number = await cuda_manager.use_cuda()

                await asyncio.to_thread(
                    generate_image_sd, image_path=image_path, prompt=prompt, x=x, y=y, negative_prompt=negative_prompt,
                    steps=steps, seed=seed, cuda_number=cuda_number, refine=refine
                )

                await cuda_manager.stop_use_cuda(cuda_number)
            await send_file(ctx=ctx, file_path=image_path)
            await ctx.respond(
                f"Картинка: {i + 1}/{repeats}\nЗапрос:{prompt}\nПотрачено: {timer.count_time()}" + seed_text)
        except Exception as e:
            await ctx.respond(f"Ошибка:{e}")
            await cuda_manager.stop_use_cuda(cuda_number)

    await ctx.defer()

    if seed and api:
        await ctx.send("seed игнорируется, так как включён API")
    if not steps == 50 and api:
        await ctx.send("steps игнорируется, так как включён API")
    if refine and api:
        await ctx.send("refine игнорируется, так как включён API")
    if not style == "DEFAULT" and not api:
        await ctx.send("style игнорируется, так как выключен API")
    if gpt:
        prompt = await image_prompt_with_gpt(prompt)
        await ctx.send(f"Запрос:\n{prompt}")

    for i in range(repeats):
        asyncio.create_task(repeat_generate_images(seed, i))


@bot.slash_command(name="inpaint_image", description='изменить изображение нейросетью')
async def __image_change(ctx,
                         image: Option(discord.SlashCommandOptionType.attachment, description='Изображение',
                                       required=True),
                         prompt: Option(str, description='запрос', required=True),
                         mask: Option(discord.SlashCommandOptionType.attachment,
                                      description='Маска. Будут изменены только БЕЛЫЕ пиксели (All)',
                                      required=False, default=None),
                         invert: Option(bool, description='изменить всё, КРОМЕ белых пикселей (False)', required=False,
                                        default=False),
                         negative_prompt: Option(str, description='негативный запрос (None)', default=".",
                                                 required=False),
                         steps: Option(int, description='число шагов (50)', required=False,
                                       default=50,
                                       min_value=1,
                                       max_value=100),
                         strength: Option(float, description='насколько сильны будут изменения (0.5)', required=False,
                                          default=0.5, min_value=0,
                                          max_value=1),
                         seed: Option(int,
                                      description='Сид (random)',
                                      required=False,
                                      default=None, min_value=1,
                                      max_value=9999999999),
                         repeats: Option(int,
                                         description='Количество повторов (1)',
                                         required=False,
                                         default=1, min_value=1,
                                         max_value=16),
                         consistently: Option(bool,
                                              description="Увеличивать изменение картинки последовательно (False)",
                                              required=False,
                                              default=False),
                         refine: Option(bool, description="Улучить изображение (False)", required=False,
                                        default=False)

                         ):
    async def images_change_async(seed, i, image_path):
        try:
            cuda_number = await cuda_manager.use_cuda()
            seed = random.randint(1, 9999999999) if seed is None else seed // (i + 1)
            await asyncio.sleep((i % 2) / 4 + 0.05)

            timer = Time_Count()

            if not consistently:
                image_path = f"images/image{ctx.author.id}_change{i}.png"

            await asyncio.to_thread(
                inpaint_image, cuda_number=cuda_number, prompt=prompt, negative_prompt=negative_prompt,
                image_path=image_path, mask_path=mask_path,
                invert=invert, strength=strength, steps=steps, seed=seed, refine=refine
            )

            # отправляем
            text = f"Изображение {i + 1}/{repeats}\nЗапрос:{prompt}\nПотрачено {timer.count_time()}.\nСид:{seed}"
            if repeats == 1:
                await ctx.respond(text)
            else:
                await ctx.send(text)

            await send_file(ctx, image_path)
        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.logging(str(traceback_str), color=Color.RED)
            await ctx.respond(f"Ошибка:{e}")
        finally:
            await cuda_manager.stop_use_cuda(cuda_number)

    await ctx.defer()

    image_path = "images/image" + str(ctx.author.id) + "_change.png"
    await image.save(image_path)

    mask_path = None
    if mask:
        mask_path = "images/image" + str(ctx.author.id) + "_change_mask.png"
        await mask.save(mask_path)

    for i in range(repeats):
        asyncio.create_task(images_change_async(seed, i, image_path))


@bot.slash_command(name="example_image", description='Изменить изображение нейросетью с помощью примера')
async def __image_example(ctx,
                          image: Option(discord.SlashCommandOptionType.attachment, description='Изображение',
                                        required=True),
                          example: Option(discord.SlashCommandOptionType.attachment, description='Изображение',
                                          required=True),
                          mask: Option(discord.SlashCommandOptionType.attachment,
                                       description='Маска. Будут изменены только БЕЛЫЕ пиксели (All)',
                                       required=False, default=None),
                          invert: Option(bool, description='изменить всё, КРОМЕ белых пикселей (False)', required=False,
                                         default=False),
                          steps: Option(int, description='число шагов (50)', required=False,
                                        default=50,
                                        min_value=1,
                                        max_value=100),
                          seed: Option(int,
                                       description='Сид (random)',
                                       required=False,
                                       default=None, min_value=1,
                                       max_value=9999999999),
                          repeats: Option(int,
                                          description='Количество повторов (1)',
                                          required=False,
                                          default=1, min_value=1,
                                          max_value=16)
                          ):
    async def images_example_async(seed, i):
        try:
            cuda_number = await cuda_manager.use_cuda()
            if not i == 0 or seed is None:
                seed = random.randint(1, 9999999999)

            timer = Time_Count()

            await asyncio.to_thread(
                generate_image_with_example, image_path=image_path, mask_path=mask_path, example_path=example_path,
                steps=steps, seed=seed, invert=invert, cuda_number=cuda_number
            )

            # отправляем
            text = f"Изображение {i + 1}/{repeats}\nПотрачено {timer.count_time()}.\nСид:{seed}"
            if repeats == 1:
                await ctx.respond(text)
            else:
                await ctx.send(text)

            await send_file(ctx, image_path)

        except Exception as e:
            traceback_str = traceback.format_exc()
            logger.logging(str(traceback_str), color=Color.RED)
            await ctx.respond(f"Ошибка:{e}")
        finally:
            await cuda_manager.stop_use_cuda(cuda_number)

    await ctx.defer()

    image_path = "images/image" + str(ctx.author.id) + "_example.png"
    await image.save(image_path)

    example_path = "images/image" + str(ctx.author.id) + "_example_example.png"
    await example.save(example_path)

    mask_path = None
    if mask:
        mask_path = "images/image" + str(ctx.author.id) + "_example_mask.png"
        await mask.save(mask_path)

    for i in range(repeats):
        asyncio.create_task(images_example_async(seed, i))


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
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Произошла ошибка: {e}")


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


@bot.slash_command(name="say", description='Сказать роботу что-то')
async def __say(
        ctx,
        text: Option(str, description='Сам текст/команда. Список команд: \\help-say', required=True),
        gpt_mode: Option(str, description="модификация GPT. Модификация сохраняется при следующих запросах!",
                         choices=["быстрый режим", "много ответов"], required=False,
                         default=None),
        custom_prompt: Option(str, description="Кастомный запрос (None)", choices=custom_prompts_files,
                              required=False,
                              default=None)
):
    # ["fast", "all", "None"], ["быстрый режим", "много ответов (медленный)", "Экономный режим"]
    user = DiscordUser(ctx)
    if gpt_mode:
        gpt_mode = gpt_mode.replace("быстрый режим", "Fast").replace("много ответов", "All")
        await user.set_user_config(SQL_Keys.gpt_mode, gpt_mode)
    else:
        gpt_mode = user.gpt_mode

    try:
        if not gpt_mode:
            gpt_mode = "Fast"
        _, text = await moderate_mat_in_sentence(text)

        gpt_role = None
        if custom_prompt:
            with open(f"gpt_history/prompts/{custom_prompt}") as file:
                content = file.read()
            text = content + text
            user.id = 0
        else:
            gpt_role = user.character.gpt_info

        chatGPT = ChatGPT()
        answer = await chatGPT.run_all_gpt(f"{user.name}:{text}", user_id=user.id, gpt_role=gpt_role, mode=gpt_mode)
        await ctx.respond(answer)
        audio_player = AudioPlayerDiscord(ctx)
        if user.character.name in await get_voice_list():
            audio_path_1 = f"{user.id}-{user.character.name}-say-row.mp3"
            audio_path_2 = f"{user.id}-{user.character.name}-say.mp3"
            await user.character.text_to_speech(answer, audio_path=audio_path_1, output_name=audio_path_2)
            await audio_player.play(audio_path_2)

            os.remove(audio_path_1)
            os.remove(audio_path_2)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
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
        voice_name: Option(str, description='Голос для озвучки (User character)', required=False, default=None),
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
    user = DiscordUser(ctx)
    if not voice_name:
        voice_name = user.character.name
    elif not user.character.name == voice_name:
        await ctx.send("Обновлена базовая модель на:" + voice_name)
        await user.set_user_config(SQL_Keys.AIname, voice_name)

    voices = await get_voice_list()
    if str(voice_name) not in voices:
        return await ctx.response.send_message("Выберите голос для озвучки (или /add_voice): " + ';'.join(voices))

    if voice_model_eleven == "All":
        voice_models = ALL_VOICES.keys()
    else:
        if voice_model_eleven is None:
            voice_model_eleven = user.character.voice_model_eleven
            if voice_model_eleven is None:
                return await ctx.response.send_message(
                    f"Голосовая модель персонажа: {voice_model_eleven}, что недопустимо")
        if voice_model_eleven not in ALL_VOICES.keys():
            await ctx.response.send_message("Список голосов elevenlabs: \n" + ';'.join(ALL_VOICES.keys()))
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

            await ctx.respond("Потрачено на обработку:" + timer.count_time())
            if output:
                if output.startswith("1"):
                    await send_file(ctx, audio_path_2)
                elif output.startswith("2"):
                    await send_file(ctx, audio_path_1)
                    await send_file(ctx, audio_path_2)

            os.remove(audio_path_1)
            os.remove(audio_path_2)
        # await cuda_manager.stop_use_cuda(cuda_number)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Ошибка при озвучивании текста (с параметрами {text}): {e}")
        # перестаём использовать видеокарту
        # await cuda_manager.stop_use_cuda(cuda_number)


@bot.slash_command(name="bark", description='Тестовая генерация речи с помощью bark')
async def __bark(
        ctx,
        text: Option(str, description='Текст для озвучки', required=True),
        speaker: Option(int, description='Голосовая модель bark (1)', required=False, default=1, min_value=1,
                        max_value=8),
        gen_temp: Option(float, description='Разнообразие (0.6)', required=False, default=0.6)
):
    global bark_model

    mat_found, text = await moderate_mat_in_sentence(text)
    if mat_found:
        await ctx.respond("Такое точно нельзя произносить!")
        return

    timer = Time_Count()
    if bark_model is None:
        await ctx.respond('Загрузка модели...')
        bark_model = BarkTTS()
        await ctx.respond('Модель загружена!')
    await cuda_manager.use_cuda(index=0)
    try:
        audio_path = f"{ctx.author.id}-{speaker}-bark.mp3"
        await bark_model.text_to_speech_bark(text=text, speaker=speaker, gen_temp=gen_temp, audio_path=audio_path)
        await send_file(ctx, audio_path)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.send(f'Ошибка при команде bark: {e}')
    await ctx.respond(timer.count_time())
    await cuda_manager.stop_use_cuda(0)


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
            await send_file(ctx, file_path)
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
                                        output_format, output, ctx):
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
                                            output_format=output_format, cuda_number=cuda_number)
        await send_output(ctx=ctx, audio_path=audio_path, output=output, timer=timer)
        await cuda_manager.stop_use_cuda(cuda_number)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Ошибка при изменении голоса(ID:d5): {e}")


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
            logger.logging(str(traceback_str), color=Color.RED)
            logger.logging(f"Произошла ошибка при извлечении плейлиста", color=Color.RED)
            return []

    param_string = None
    # ["link", "file", "all_files", "None"], ["ссылка на все файлы", "только результат (1 файл)", "все файлы", "не отправлять"]
    output = output.replace("ссылка на все файлы", "link").replace("только результат (1 файл)", "file").replace(
        "все файлы", "all_files").replace("не отправлять", "None")
    try:
        await ctx.defer()
        user = DiscordUser(ctx)

        if not voice_name:
            voice_name = user.character.name
        elif not user.character.name == voice_name:
            await ctx.send("Обновлена базовая модель на:" + voice_name)
            await user.set_user_config(SQL_Keys.AIname, voice_name)

        voices = await get_voice_list()
        if voice_name not in voices:
            await ctx.respond("Выберите голос для озвучки (или /add_voice):" + ', '.join(voices))
            return

        if pitch is None:
            pitch = user.character.pitch

        logger.logging("suc params", color=Color.CYAN)

        urls = []
        if audio_path:
            filename = f"{ctx.author.id}-{random.randint(1, 1000000)}.mp3"
            await audio_path.save(filename)
            urls.append(filename)
            if only_voice_change:
                cuda_number = await cuda_manager.use_cuda()
                voice_changer = Voice_Changer(cuda_number=cuda_number, voice_name=voice_name, index_rate=indexrate,
                                              pitch=pitch, filter_radius=filter_radius, rms_mix_rate=rms_mix_rate,
                                              protect=0.3, algo=palgo)
                await voice_changer.voice_change(input_path=filename, output_path=filename)
                await send_file(ctx, file_path=filename)
                await cuda_manager.stop_use_cuda(cuda_number)
                return
        if url:
            if ";" in url:
                urls += url.split(";")
            elif "playlist" in url:
                urls += (await get_links_from_playlist(url)).split(";")
            else:
                urls.append(url)

        for i, url in enumerate(urls):
            asyncio.create_task(
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
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Ошибка при изменении голоса(ID:d5) (с параметрами {param_string}): {e}")
        await cuda_manager.stop_use_cuda(cuda_number)


@bot.slash_command(name="create_dialog", description='Имитировать диалог людей')
async def __dialog(
        ctx,
        names: Option(str, description="Участники диалога через ';' (у каждого должен быть добавлен голос!)",
                      required=True),
        theme: Option(str, description="Начальная тема разговора (случайная тема)", required=False,
                      default="случайная тема"),
        prompt: Option(str, description="Общий запрос для всех диалогов (None)", required=False, default="")
):
    try:
        await ctx.respond('Выполнение...')
        names = names.split(";")
        voices = await get_voice_list()
        for name in names:
            if name not in voices:
                await ctx.respond("Выберите голос для озвучки (или /add_voice):" + ', '.join(voices))
                return

        # не в войс чате
        voice = ctx.author.voice
        if not voice:
            return await ctx.respond(voiceChannelErrorText)

        # остановка записи
        author_id = ctx.author.id
        if author_id in recognizers:
            recognizer = recognizers[author_id]
            if recognizer:
                await recognizer.stop_recording()

        Dialog_AI(ctx, names, theme, prompt)
    except discord.ApplicationCommandInvokeError:
        await ctx.respond(f"Я и так тебя не слушал ._.")
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.respond(f"Ошибка при диалоге: {e}")


class Dialog_AI:
    def __init__(self, ctx, characters, theme, global_prompt):

        if ctx.guild_id in dialogs:
            asyncio.run(ctx.send("Уже идёт диалог"))
            return

        self.alive = True
        self.ctx = ctx
        dialogs[self.ctx.guild.id] = self

        self.characters = []
        self.names = []
        self.infos = []

        for i, name in enumerate(characters):
            character = Character(name=name)
            asyncio.run(character.load_voice(i % 2, max_simbols=500))
            self.characters.append(character)
            self.names.append(character.name)
            self.infos.append(character.info.replace("Вот информация о тебе:", f"Вот информация о {character.name}:"))

        self.theme = theme
        self.global_prompt = global_prompt
        self.audio_player = AudioPlayerDiscord(ctx)
        asyncio.run(self.audio_player.join_channel())

        self.recognizer = Recognizer(ctx=ctx, with_gpt=False)

        self.play_number = 0
        self.files_number = 0
        self.gpt = ChatGPT(warnings=True, save_history=False)
        self.user_id = ctx.author.id * 10

        self.dialog_create = {}
        self.dialog_play = {}

        self.text_file = f"gpt_history/history-{self.ctx.guild.id}.txt"

        if not os.path.exists(self.text_file):
            with open(self.text_file, "w", encoding="utf-8"):
                pass
        with open(self.text_file, "a", encoding="utf-8") as writer:
            writer.write("\n\n" + ', '.join(self.names))

        asyncio.create_task(self.gpt_dialog())
        asyncio.create_task(self.play_dialog())
        functions = [self.create_audio_dialog(character) for character in self.characters]
        for function in functions:
            asyncio.create_task(function)

    async def stop_dialog(self):
        if self.ctx.guild.id in dialogs:
            del dialogs[self.ctx.guild.id]
            self.alive = False

    async def play_dialog(self):
        while self.alive:
            if self.play_number in self.dialog_play:
                name, audio_path = self.dialog_play[self.play_number]
                audio_path = os.path.abspath(audio_path)
                del self.dialog_play[self.play_number]

                self.play_number += 1

                await self.ctx.send("говорит " + name)

                last_removed_key = self.characters[0].voice.elevenlabs_removed_key
                if last_removed_key:
                    await self.ctx.send("Last key:" + last_removed_key)
                await self.audio_player.play(audio_path)
                await self.ctx.send("end")
            else:
                # logger.logging("warn: Нет аудио для диалога!", color=Color.RED)
                await asyncio.sleep(0.75)

    async def create_audio_dialog(self, character):
        while self.alive:
            try:
                for files_number, (name, text) in self.dialog_create.items():
                    if files_number - self.play_number > 2:
                        continue

                    if name == character.name:
                        # logger.logging(f"Found file: ({files_number}, {self.play_number}). Voice:{character.name}")

                        while not len(self.dialog_play) == 0 and not self.audio_player.isPlaying:
                            # logger.logging("wait for play smth", color=Color.GRAY)
                            await asyncio.sleep(0.25)
                        del self.dialog_create[files_number]
                        audio_path_1 = f"{files_number}{character.name}-row.mp3"
                        audio_path_2 = f"{files_number}{character.name}.mp3"
                        await character.text_to_speech(text=text, audio_path=audio_path_1, output_name=audio_path_2)
                        self.dialog_play[files_number] = (character.name, audio_path_2)
                        os.remove(audio_path_1)
                        break
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.logging(str(e), color=Color.RED)

    async def save_dialog(self, result):
        # logger.logging(result, color=Color.GRAY)
        lines = result.split("\n")
        with open(self.text_file, "a", encoding="utf-8") as writer:
            found_max_line = 0
            for i, line in enumerate(lines):
                for name in self.names:
                    # Человек: привет
                    # Человек (man): привет
                    # Чэловек: привет
                    if (line.startswith(name) or line.startswith(name.replace("э", "е"))) and ":" in line:
                        line = line[line.find(":") + 1:]
                        self.dialog_create[self.files_number] = (name, line)
                        self.files_number += 1
                        writer.write(f"{name}:{line}\n")
                        found_max_line = i
                        break
        return ''.join(lines[found_max_line + 1:])

    async def run_gpt(self, prompt):
        result = await self.gpt.run_all_gpt(prompt=prompt, user_id=self.user_id)
        if "(" in result and ")" in result:
            result = re.sub(r'\(.*?\)', '', result)
        if "*" in result:
            result = re.sub(r'\*.*?\*', '', result)
        return result.replace("[", "").replace("]", "").replace(
            "Привет, ребята! ", "").replace("Привет, ребята", "").replace("Всем привет, ", "").replace("Эй", "")

    async def gpt_dialog(self):
        infos = '.\n'.join(self.infos)
        prompt = (
            f"# Задача\nСоздать диалог между {', '.join(self.names)}.\n"
            f"# Тема диалога\n{self.theme}.\n"
            f"# Информация\n{infos}.\n"
            f"# {self.global_prompt}.\n\n"
            f"# Требования\n"
            f"1. Персонажи должны быть правдоподобными и действовать согласно своему характеру.\n"
            f"2. В конце диалога укажите кратко, что произошло и что ожидается в следующем диалоге.\n"
            f"3. Диалог должен быть в формате:\n[Говорящий]: [Произнесенный текст]."
        )
        result = await self.run_gpt(prompt)

        dialog_next = await self.save_dialog(result)

        # logger.logging("DIALOG NEXT:", dialog_next, color=Color.GRAY)

        theme_last = self.theme
        theme_was_in_row = 0
        while self.alive:
            try:

                spoken_text = self.recognizer.recognized
                if spoken_text:
                    spoken_text = "\n0. Отвечай зрителям! Зрители за прошлый диалог написали:\"" + spoken_text + "\"\n"
                    self.recognizer.recognized = ""

                # Тема добавляется в запрос, если она изменилась
                new_theme = self.theme
                if not theme_last == new_theme:
                    theme_was_in_row = 0
                    theme_last = new_theme
                    theme_temp = f"Тема диалога: \"{new_theme}\""
                    with open(f"caversAI/history-{self.ctx.guild.id}", "a", encoding="utf-8") as writer:
                        writer.write(f"\n==Новая тема==: {new_theme}\n\n")
                elif theme_was_in_row > 1:
                    self.theme = await self.run_gpt(
                        f"Придумай новую тему для этого диалога:\n{result}\n\nВ ответе выведи 2-3 слова в качестве следующей темы для диалога")
                    theme_last = self.theme
                    theme_temp = self.theme
                    theme_was_in_row = 0
                else:
                    theme_was_in_row += 1
                    theme_temp = f"Изначальная тема диалога: \"{new_theme}\""
                prompt = (
                    f"# Задача\nПродолжите диалог между {', '.join(self.names)}.\n"
                    f"# {theme_temp}.\n"
                    f"# Информация\n{'.'.join(self.infos)}.\n"
                    f"# {self.global_prompt}.\n\n"
                    f"# Требования\n"
                    f"{spoken_text}"
                    f"1. Персонажи должны действовать согласно своему характеру.\n"
                    f"2. Не используйте приветствия в начале диалога.\n"
                    f"3. Не повторяйте предыдущий диалог. Описание предыдущего диалога: \"{dialog_next}\".\n"
                    f"4. В конце диалога кратко укажите, что произошло в этом диалоге и что должно произойти дальше.\n"
                    f"5. Представьте диалог в формате:\n[Говорящий]: [Произнесенный текст]."
                )

                result = await self.run_gpt(prompt)

                dialog_next = await self.save_dialog(result)

                # Слишком большой разрыв
                while self.files_number - self.play_number > 2:
                    # logger.logging(f"wait, difference > 4 ({self.files_number},{self.play_number})", color=Color.YELLOW)
                    await asyncio.sleep(5)
                    if not self.alive:
                        return

                # Слишком много текста
                while len(self.dialog_create) > 2:
                    # logger.logging("wait, too many text > 2", color=Color.YELLOW)
                    await asyncio.sleep(5)
                    if not self.alive:
                        return

            except Exception as e:
                traceback_str = traceback.format_exc()
                logger.logging(str(traceback_str), color=Color.RED)
                await self.ctx.send(f"Ошибка при изменении голоса(ID:d4): {e}")


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
    except Exception:
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
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = process.communicate()
        for line in stdout.decode().split('\n'):
            if line.strip():
                await ctx.author.send(line)
        for line in stderr.decode().split('\n'):
            if line.strip():
                await ctx.author.send(line)
    except subprocess.CalledProcessError as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.author.send(f"Ошибка выполнения команды: {e}")
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.author.send(f"Произошла неизвестная ошибка: {e}")


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
    await send_file(ctx=ctx, file_path=file_path)


@bot.command(aliases=['restart'], help="Перезагрузка")
async def command_restart(ctx):
    owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
    if str(ctx.author.id) not in owner_ids:
        await ctx.author.send("Доступ запрещён")
        return
    await ctx.send("Перезагрузка")
    await set_get_config_all("Default", SQL_Keys.reload, ctx.author.id)
    exit(0)


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
    exit(0)
    # asyncio.create_task(command_line(ctx=ctx, command="pkill -f python"))


@bot.command(aliases=['clear'], help="Отчистить память")
async def command_clear(ctx):
    owner_ids = (await set_get_config_all("Default", SQL_Keys.owner_id)).split(";")
    if str(ctx.author.id) not in owner_ids:
        await ctx.author.send("Доступ запрещён")
        return
    await set_get_config_all("Default", SQL_Keys.reload, "clear")
    import os
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


@bot.command(aliases=['themer'], help="тема для диалога")
async def themer_set(ctx, *args):
    text = " ".join(args)
    guild_id = ctx.guild.id
    if guild_id in dialogs:
        dialog = dialogs[guild_id]
        if dialog:
            dialog.theme = text
            await ctx.send("Изменена тема:" + text)


@bot.slash_command(name="record", description='воспринимать команды из микрофона')
async def record(ctx):
    global recognizers, audio_players, dialogs
    author_id = ctx.author.id

    if author_id in recognizers:
        recognizer = recognizers[author_id]
        if recognizer:
            await recognizer.stop_recording()

    voice = ctx.author.voice
    if not voice:
        return await ctx.respond(voiceChannelErrorText)
    try:
        Recognizer(ctx)
    except:
        recognizers = {}
        audio_players = {}
        dialogs = {}
        Recognizer(ctx)


@bot.slash_command(name="stop_recording", description='перестать воспринимать команды из микрофона')
async def stop_recording(ctx):
    author_id = ctx.author.id

    if author_id in recognizers:
        recognizer = recognizers[author_id]
        if recognizer:
            await recognizer.stop_recording()
            await ctx.respond("Остановка записи.")
        else:
            await ctx.respond("Я и так тебя не слышал ._.")
    else:
        await ctx.respond("Я и так тебя не слышал ._.")


class Recognizer:
    def __init__(self, ctx, with_gpt=True):
        if ctx.author.id in recognizers:
            asyncio.run(ctx.send("Уже слушаю вас"))
            return

        self.alive = True
        self.ctx = ctx
        self.stream_sink = StreamSink(ctx=ctx)
        self.google_recognizer = sr.Recognizer()
        self.not_speaking = 0
        self.delay_record = float(
            asyncio.run(set_get_config_all("Default", SQL_Keys.delay_record)) if not None else 5) * 10
        self.user = DiscordUser(ctx)

        self.with_gpt = with_gpt
        self.recognized = ""

        self.audio_player = AudioPlayerDiscord(ctx)
        self.vc = None
        asyncio.run(ctx.respond("Внимательно вас слушаю"))
        asyncio.run(self.initialize())
        asyncio.create_task(self.recognize())

    async def initialize(self):
        if not self.audio_player.voice_client:
            await self.audio_player.join_channel()
        self.vc = self.audio_player.voice_client

        if self.vc is None:
            await self.ctx.respond("Ошибка")

        recognizers[self.ctx.author.id] = self
        self.stream_sink.set_user(self.ctx.author.id)
        self.vc.start_recording(
            self.stream_sink,
            self.once_done,
            self.ctx.channel
        )

    async def once_done(self, _1, _2):
        logger.logging("Once done", type(_1), _1, type(_2), _2, Color.GRAY)

    async def stop_recording(self):
        if self.ctx.author.id in recognizers:
            del recognizers[self.ctx.author.id]
            del audio_players[self.ctx.guild.id]
            logger.logging("RECOGNIZERS LEFT:", recognizers)
            self.alive = False
            if self.vc:
                self.vc.stop_recording()
                await self.vc.disconnect(force=True)
            else:
                logger.logging("Cant stop recording: None")
        else:
            logger.logging("Cant stop recording: No user")

    async def recognize(self):
        await self.user.character.load_voice(1)
        google_recognizer = self.google_recognizer
        logger.logging("Record", color=Color.GRAY)
        while self.alive:
            speaking = self.stream_sink.buffer.speaking
            audio_file = self.stream_sink.buffer.previous_audio_filename
            if not speaking:
                # logger.logging("Not speaking", color=Color.GRAY)
                self.not_speaking += 1

                await asyncio.sleep(0.1)
                if audio_file is None:
                    continue
                # если долго не было файлов (человек перестал говорить)
                if self.not_speaking > self.delay_record:
                    text = None
                    self.not_speaking = 0
                    # распознание речи
                    try:
                        with sr.AudioFile(audio_file) as source:
                            audio_data = google_recognizer.record(source)
                            text = google_recognizer.recognize_google(audio_data, language="ru-RU")
                    except sr.UnknownValueError:
                        pass
                    except Exception:
                        traceback_str = traceback.format_exc()
                        logger.logging(str(traceback_str), color=Color.RED)

                    # удаление out_all.wav
                    self.stream_sink.buffer.previous_audio_filename = None
                    Path(audio_file).unlink(missing_ok=True)
                    # создание пустого файла
                    AudioSegment.silent(duration=0).export(audio_file, format="wav")

                    if not text is None:
                        mat_found, text_out = await moderate_mat_in_sentence(text)
                        logger.logging("STT:", text_out, color=Color.GREEN)
                        if self.with_gpt:
                            chatGPT = ChatGPT()
                            answer = await chatGPT.run_all_gpt(f"{self.user.name}:{text_out}",
                                                               user_id=self.user.id,
                                                               gpt_role=self.user.character.gpt_info)
                            await self.ctx.send(answer)
                            if self.user.character.name in await get_voice_list():
                                audio_path_1 = f"{self.user.id}-{self.user.character.name}-record-row.mp3"
                                audio_path_2 = f"{self.user.id}-{self.user.character.name}-record.mp3"
                                await self.user.character.text_to_speech(answer, audio_path=audio_path_1,
                                                                         output_name=audio_path_2)
                                await self.audio_player.play(audio_path_2)

                                os.remove(audio_path_1)
                                os.remove(audio_path_2)

                        else:
                            self.recognized += text_out + " "
            else:
                # logger.logging("Speaking", color=Color.GRAY)
                self.stream_sink.buffer.speaking = False
                self.not_speaking = 0
                await asyncio.sleep(self.stream_sink.buffer.block_len)

        logger.logging("Stop_Recording", color=Color.GREEN)


async def send_file(ctx, file_path, delete_file=False):
    try:
        try:
            await ctx.respond(file=discord.File(file_path))
        except:
            await ctx.send(file=discord.File(file_path))
        if delete_file:
            await asyncio.sleep(1.5)
            os.remove(file_path)
    except FileNotFoundError:
        await ctx.send('Файл не найден.')
    except discord.HTTPException as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        await ctx.send(f'Произошла ошибка при отправке файла: {e}.')


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
                await send_file(self.ctx, audio_file)
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
        logger.logging("====load bot====", color=Color.CYAN)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot.start(discord_token))
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        logger.logging(f"Произошла ошибка", color=Color.RED)
