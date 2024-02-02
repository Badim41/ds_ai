import asyncio
import os
import re
import subprocess
import zipfile
from pydub import AudioSegment

import json
from gtts import gTTS
from elevenlabs import generate, save, set_api_key, VoiceSettings, Voice

from cover_gen import run_ai_cover_gen
from discord_bot import send_file, playSoundFileDiscord
from discord_tools.detect_mat import moderate_mat_in_sentence
from discord_tools.logs import Color, Logs
from discord_tools.timer import Time_Count
from voice_change import Voice_Changer
from use_free_cuda import Use_Cuda
from discord_tools.secret import load_secret, SecretKey, create_secrets

logger = Logs()


class AI_Cover:
    def __init__(self, use_cuda: Use_Cuda):
        self.cuda = use_cuda

    async def make_cover(self, url, ctx, voice, pitch=0, time=-1, indexrate=0.5,
                         filter_radius=3, loudness=0.2, mainVocal=0, backVocal=0, music=0,
                         roomsize=0.2, wetness=0.1, dryness=0.85, start=0, output="None",
                         algo="rmvpe", hop=128, output_format="mp3"):

        timer = Time_Count()

        cuda = await self.cuda.use_cuda()

        audio_path = run_ai_cover_gen(url, voice, pitch, indexrate, filter_radius, loudness,
                                      algo, hop, 0.33, mainVocal, backVocal, music,
                                      0, roomsize, wetness, dryness, 0.7,
                                      output_format, cuda)

        await self.cuda.stop_use_cuda(cuda)

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
        await playSoundFileDiscord(ctx=ctx, audio_file_path=audio_path, duration=time, start_seconds=start)

        if not output == "None":
            await ctx.send(timer.count_time())

        else:
            await ctx.send("Произошла ошибка")


async def execute_command(command, ctx):
    # print(command)
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        for line in stdout.decode().split('\n'):
            if line.strip():
                await logger.logging(line, Color.GRAY)
                # await ctx.send(line)
    except subprocess.CalledProcessError as e:
        await ctx.send(f"Ошибка выполнения команды (ID:f8): {e}")
    except Exception as e:
        await ctx.send(f"Произошла неизвестная ошибка (ID:f9): {e}")


async def get_link_to_file(zip_name, ctx):
    try:
        process = await asyncio.create_subprocess_shell(
            f"curl -T \"{zip_name}\" https://pixeldrain.com/api/file/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
        )

        stdout, stderr = await process.communicate()

        for line in stdout.decode().split('\n'):
            if line.strip():
                print(line)
                # {"id":"123"}
                if "id" in line:
                    line = line[line.find(":") + 2:]
                    line = line[:line.find("\"")]
                    return "https://pixeldrain.com/u/" + line
    except subprocess.CalledProcessError as e:
        await ctx.send(f"Ошибка выполнения команды (ID:z1): {e}")
    except Exception as e:
        await ctx.send(f"Произошла неизвестная ошибка (ID:z2): {e}")


async def speed_up_audio(input_file, speed_factor):
    audio = AudioSegment.from_file(input_file)
    if speed_factor <= 1:
        return
    else:
        sped_up_audio = audio.speedup(playback_speed=speed_factor)
        sped_up_audio.export(input_file, format="mp3")


class TextToSpeechRVC:
    def __init__(self, voice_name, voice_class=None, index_rate=0.5, pitch=0, pitch_change=0, filter_radius=3,
                 rms_mix_rate=0.3,
                 protect=0.33, algo="rmvpe", speed=1, voice_model_eleven="Adam", stability=0.4,
                 similarity_boost=0.25,
                 style=0.4, max_simbols=300, speaker_boost=True):
        if voice_class is None:
            voice_class = Voice_Changer(0, voice_model, index_rate=index_rate, pitch=pitch,
                                        filter_radius=filter_radius, rms_mix_rate=rms_mix_rate, protect=protect,
                                        algo=algo)
        self.voice_name = voice_name
        self.voice_class = voice_class
        self.pitch_change = pitch_change
        self.voice_model_eleven = voice_model_eleven
        self.speed = speed
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.max_simbols = max_simbols
        self.speaker_boost = speaker_boost
        self.elevenlabs_voice_keys = load_secret(SecretKey.voice_keys)

    async def text_to_speech(self, text, audio_path="1.mp3", output_name="2.mp3"):
        if text is None or text.replace("\n", "").replace(" ", "") == "":
            await logger.logging(f"Пустой текст \"{text}\"", Color.RED)
            raise "No text"
        mat_found, text = await moderate_mat_in_sentence(text)

        # убираем текст до коментария
        if "||" in text:
            text = re.sub(r'\|\|.*?\|\|', '', text)
        if "```" in text:
            text = re.sub(r'```.*?```', '', text)

        audio_path = "1.mp3"
        if output_name is None:
            output_name = f"{self.voice_model_eleven}.mp3"

        await self.elevenlabs_text_to_speech(text, audio_path)

        await self.voice_changer(audio_path, output_name, self.pitch_change)

    async def elevenlabs_text_to_speech(self, text, audio_file):
        max_simbols = self.max_simbols

        if len(text) > max_simbols:
            await logger.logging("gtts", text, color=Color.YELLOW)
            await self.gtts(text, audio_file, language="ru")
            self.pitch_change -= 12
        else:
            # получаем ключ для elevenlab
            key = self.elevenlabs_voice_keys[0]
            if not key == "Free":
                set_api_key(key)

            try:
                voice_id = await self.get_elevenlabs_voice_id_by_name()
                # print("VOICE_ID_ELEVENLABS:", voice_id)
                audio = generate(
                    text=text,
                    model='eleven_multilingual_v2',
                    voice=Voice(
                        voice_id=voice_id,
                        settings=VoiceSettings(stability=self.stability, similarity_boost=self.similarity_boost,
                                               style=self.style,
                                               use_speaker_boost=self.speaker_boost)
                    ),
                )

                save(audio, audio_file)
            except Exception as e:
                await logger.logging(f"Ошибка при выполнении команды (ID:f16): {e}", color=Color.RED)
                if "Please play" in str(e):
                    create_secrets(SecretKey.voice_keys, "None")
                self.elevenlabs_voice_keys = self.elevenlabs_voice_keys[1:]
                create_secrets(SecretKey.voice_keys, ';'.join(self.elevenlabs_voice_keys))
                await self.elevenlabs_text_to_speech(text, audio_file)

    async def gtts(self, tts, output_file, language="ru"):
        voiceFile = gTTS(tts, lang=language)
        voiceFile.save(output_file)

    async def voice_changer(self, input_path, output_path, pitch_change):
        audio_path = self.voice_class.voice_change(input_path, output_path, pitch_change=pitch_change)
        await logger.logging("done RVC", Color.GREEN)
        await speed_up_audio(audio_path, self.speed)
        return audio_path

    async def get_elevenlabs_voice_id_by_name(self):
        with open('voices.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        voice = next((v for v in data["voices"] if v["name"] == self.voice_name), None)
        return voice["voice_id"] if voice else None


class Character:
    def __init__(self, name):
        json_file_path = os.path.join(f'rvc_models', name, "params.json")
        with open(json_file_path, 'r') as json_file:
            json_data = json.load(json_file)

        self.info = json_data["info"]
        self.gender = json_data["gender"]
