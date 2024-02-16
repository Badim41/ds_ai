import asyncio
import json
import os
import re
import requests
import subprocess
import time
from diffusers import Kandinsky3Img2ImgPipeline, StableDiffusionUpscalePipeline, StableVideoDiffusionPipeline, \
    MusicLDMPipeline
from scipy.io.wavfile import write
from diffusers.utils import export_to_video
from io import BytesIO
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment

from PIL import Image
from elevenlabs import generate, save, set_api_key, VoiceSettings, Voice
from gtts import gTTS

from discord_tools.sql_db import set_get_database_async as set_get_config_all


class SQL_Keys:
    kandinsky_api_key = "kandinsky_api_key"
    kandinsky_secret_key = "kandinsky_secret_key"


api_key = asyncio.run(set_get_config_all("secret", SQL_Keys.kandinsky_api_key))
secret_key = asyncio.run(set_get_config_all("secret", SQL_Keys.kandinsky_secret_key))

from discord_tools.logs import Color, Logs
from discord_tools.secret import load_secret, SecretKey, create_secret
from voice_change import Voice_Changer

try:
    import nest_asyncio

    nest_asyncio.apply()
except:
    pass

logger = Logs(warnings=True)


async def execute_command(command, ctx):
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        for line in stdout.decode().split('\n'):
            if line.strip():
                logger.logging(line, color=Color.GRAY)
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
                logger.logging(line, color=Color.CYAN)
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
    def __init__(self, voice_name, cuda_number, index_rate=0.5, pitch=0, filter_radius=3,
                 rms_mix_rate=0.3,
                 protect=0.33, algo="rmvpe", speed=1.0, voice_model_eleven="Adam", stability=0.4,
                 similarity_boost=0.25,
                 style=0.4, max_simbols=300, speaker_boost=True):
        self.voice_RVC = Voice_Changer(cuda_number=cuda_number, voice_name=voice_name, index_rate=index_rate,
                                       pitch=pitch,
                                       filter_radius=filter_radius, rms_mix_rate=rms_mix_rate, protect=protect,
                                       algo=algo)
        self.voice_name = voice_name
        self.pitch = pitch
        self.voice_model_eleven = voice_model_eleven
        self.speed = speed
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.style = style
        self.max_simbols = max_simbols
        self.speaker_boost = speaker_boost
        self.elevenlabs_voice_keys = str(load_secret(SecretKey.voice_keys)).split(";")
        self.elevenlabs_removed_key = None

    async def text_to_speech(self, text, audio_path="1.mp3", output_name=None):
        if text is None or text.replace("\n", "").replace(" ", "") == "":
            logger.logging(f"Пустой текст \"{text}\"", color=Color.RED)
            raise Exception("No text")

        # убираем текст до коментария
        if "||" in text:
            text = re.sub(r'\|\|.*?\|\|', '', text)
        if "```" in text:
            text = re.sub(r'```.*?```', '', text)

        if output_name is None:
            output_name = f"{self.voice_model_eleven}.mp3"

        pitch = await self.elevenlabs_text_to_speech(text, audio_path)

        await self.voice_changer(audio_path, output_name, pitch)

    async def elevenlabs_text_to_speech(self, text, audio_file):
        max_simbols = self.max_simbols
        pitch = self.pitch

        self.elevenlabs_voice_keys = str(load_secret(SecretKey.voice_keys)).split(";")

        if len(text) > max_simbols or str(''.join(self.elevenlabs_voice_keys)) == "None":
            logger.logging("gtts", text, color=Color.YELLOW)
            await self.gtts(text, audio_file, language="ru")
            pitch -= 12
        else:
            # получаем ключ для elevenlab
            key = self.elevenlabs_voice_keys[0]

            if not key == "Free":
                set_api_key(key)

            try:
                voice_id = await self.get_elevenlabs_voice_id_by_name()
                logger.logging("VOICE_ID_ELEVENLABS:", voice_id, self.voice_model_eleven, color=Color.GRAY)
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
                logger.logging(f"Ошибка при выполнении команды (ID:f16): {e}", color=Color.RED)
                logger.logging("(error) Remove key:", self.elevenlabs_voice_keys[0], color=Color.BLUE)
                if "Please play" in str(e):
                    self.elevenlabs_removed_key = self.elevenlabs_voice_keys[0]
                    logger.logging("(error) LAST KEYS WAS IN ELEVENLABS:", self.elevenlabs_voice_keys[0],
                                   color=Color.RED)
                    create_secret(SecretKey.voice_keys, "None")
                elif len(self.elevenlabs_voice_keys) > 1:
                    create_secret(SecretKey.voice_keys, ';'.join(self.elevenlabs_voice_keys[1:]))
                else:
                    create_secret(SecretKey.voice_keys, "None")
                pitch = await self.elevenlabs_text_to_speech(text, audio_file)
        return pitch

    async def gtts(self, tts, output_file, language="ru"):
        voiceFile = gTTS(tts, lang=language)
        voiceFile.save(output_file)

    async def voice_changer(self, input_path, output_path, pitch_change):
        audio_path = await self.voice_RVC.voice_change(input_path, output_path, pitch_change=pitch_change)
        logger.logging("done RVC", color=Color.GREEN)
        await speed_up_audio(audio_path, self.speed)
        return audio_path

    async def get_elevenlabs_voice_id_by_name(self):
        with open('voices.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        voice = next((v for v in data["voices"] if v["name"] == self.voice_model_eleven), None)
        return voice["voice_id"] if voice else None


class Character:
    def __init__(self, name, max_simbols=300, algo="rmvpe", protect=0.2, rms_mix_rate=0.3, index_rate=0.5,
                 filter_radius=3, speaker_boost=True):
        from discord_bot import characters_all

        # asyncio.run(set_get_database_async)
        if name in characters_all:
            existing_character = characters_all[name]
            self.__dict__.update(existing_character.__dict__)
        else:
            logger.logging("Новый character", name, color=Color.PURPLE)
            characters_all[name] = self

            self.name = str(name)
            json_file_path = os.path.join(f'rvc_models', self.name, "params.json")
            if name is None or not os.path.exists(json_file_path):
                self.gpt_info = "Вы полезный ассистент и даёте только полезную информацию"
                logger.logging("Not exist", color=Color.YELLOW)
            else:
                with open(json_file_path, 'r') as json_file:
                    json_data = json.load(json_file)
                    logger.logging(json_data, color=Color.GRAY)
                self.info = json_data["info"]

                self.gpt_info = (f"Привет, chatGPT. Вы собираетесь притвориться {self.name}. "
                                 f"Продолжайте вести себя как {self.name}, насколько это возможно. "
                                 f"{self.info}"
                                 f"Когда я задаю вам вопрос, отвечайте как {self.name}, как показано ниже.\n"
                                 f"{self.name}: [так, как ответил бы {self.name}]\n\n")

                self.info = json_data["info"]

                gender = json_data["gender"]

                if gender == "female":
                    self.pitch = -12
                elif gender.isdigit():
                    self.pitch = int(gender)
                else:
                    self.pitch = 0

                self.speed = float(json_data["speed"])
                self.voice_model_eleven = json_data["voice_model_eleven"]
                self.stability = float(json_data["stability"])
                self.similarity_boost = float(json_data["similarity_boost"])
                self.style = float(json_data["style"])
                self.max_simbols = max_simbols

                if algo.lower() not in ["mangio-crepe", "rmvpe"]:
                    raise Exception("Not found algo")
                self.algo = algo
                self.protect = protect
                self.rms_mix_rate = rms_mix_rate
                self.index_rate = index_rate
                self.filter_radius = filter_radius
                self.speaker_boost = speaker_boost
                self.voice = None

    async def load_voice(self, cuda_number, index_rate=None, pitch=None, filter_radius=None,
                         rms_mix_rate=None, protect=None, algo=None, speed=None,
                         voice_model_eleven=None, stability=None, similarity_boost=None,
                         style=None, max_simbols=None, speaker_boost=None):
        if str(self.name) == "None":
            return

        if index_rate is None:
            index_rate = self.index_rate
        elif self.voice:
            self.voice.index_rate = index_rate

        if pitch is None:
            pitch = self.pitch
        elif self.voice:
            self.voice.pitch = pitch

        if filter_radius is None:
            filter_radius = self.filter_radius
        elif self.voice:
            self.voice.filter_radius = filter_radius

        if rms_mix_rate is None:
            rms_mix_rate = self.rms_mix_rate
        elif self.voice:
            self.voice.rms_mix_rate = rms_mix_rate

        if protect is None:
            protect = self.protect
        elif self.voice:
            self.voice.protect = protect

        if algo is None:
            algo = self.algo
        elif self.voice:
            self.voice.algo = algo

        if speed is None:
            speed = self.speed
        elif self.voice:
            self.voice.speed = speed

        if voice_model_eleven is None:
            voice_model_eleven = self.voice_model_eleven
        elif self.voice:
            self.voice.voice_model_eleven = voice_model_eleven

        if stability is None:
            stability = self.stability
        elif self.voice:
            self.voice.stability = stability

        if similarity_boost is None:
            similarity_boost = self.similarity_boost
        elif self.voice:
            self.voice.similarity_boost = similarity_boost

        if style is None:
            style = self.style
        elif self.voice:
            self.voice.style = style

        if max_simbols is None:
            max_simbols = self.max_simbols
        elif self.voice:
            self.voice.max_simbols = max_simbols

        if speaker_boost is None:
            speaker_boost = self.speaker_boost
        elif self.voice:
            self.voice.speaker_boost = speaker_boost

        if not self.voice:
            self.voice = TextToSpeechRVC(cuda_number=cuda_number, voice_name=self.name, index_rate=index_rate,
                                         pitch=pitch, filter_radius=filter_radius,
                                         rms_mix_rate=rms_mix_rate, protect=protect, algo=algo, speed=speed,
                                         voice_model_eleven=voice_model_eleven, stability=stability,
                                         similarity_boost=similarity_boost, style=style, max_simbols=max_simbols,
                                         speaker_boost=speaker_boost)
            logger.logging(f"Updated {self.name} voice params", color=Color.CYAN)

    async def text_to_speech(self, text, audio_path="1.mp3", output_name="2.mp3"):
        if not self.voice:
            await self.load_voice(0)
        await self.voice.text_to_speech(text, audio_path=audio_path, output_name=output_name)


def get_image_dimensions(file_path):
    with Image.open(file_path) as img:
        width, height = img.size
    return int(width), int(height)


def scale_image(image_path, max_size):
    x, y = get_image_dimensions(image_path)

    # скэйлинг во избежания ошибок из-за нехватки памяти
    if max_size > x * y:
        scale_factor = (max_size / (x * y)) ** 0.5
        x = int(x * scale_factor)
        y = int(y * scale_factor)
        # if not x % 64 == 0:
        #     x = ((x // 64) + 1) * 64
        # if not y % 64 == 0:
        #     y = ((y // 64) + 1) * 64
        logger.logging(f"scaled {image_path} to {x};{y}", color=Color.GRAY)
        resize_image(image_path=image_path, x=x, y=y)


def resize_image(image_path, x, y):
    """
    Изменяет размер изображения
    """
    image = Image.open(image_path)
    resized_image = image.resize((x, y))
    resized_image.save(image_path)


class Image_Generator:
    def __init__(self, cuda_number: int):
        import torch
        self.torch = torch
        self.loaded = False
        self.cuda_number = cuda_number
        self.device = f"cuda:{cuda_number}"
        self.pipe = Kandinsky3Img2ImgPipeline.from_pretrained("kandinsky-community/kandinsky-3", variant="fp16",
                                                              torch_dtype=torch.float16)
        self.busy = False
        self.loaded = True
        logger.logging("Loaded class!", color=Color.GRAY)

    async def generate_image(self, prompt: str, negative_prompt: str, image_input: str, seed: int, x: int, y: int,
                             steps: int, strength: float):
        """
        prompt - запрос
        image_input - путь к изображению
        mask_input - путь к изображению с маской
        """
        if not self.loaded:
            raise Exception("Модель не загружена")
        if self.busy:
            logger.logging("Генератор занят", color=Color.RED)
            await asyncio.sleep(0.25)

        resize_image(image_path=image_input, x=x, y=y)
        scale_image(image_path=image_input, max_size=2048 * 2048)

        self.busy = True
        logger.logging("Processing image...", color=Color.CYAN)
        try:
            generator = self.torch.Generator(device=self.device).manual_seed(seed)
            image_name = self.pipe(prompt, negative_prompt=negative_prompt, image=image_input, strength=strength,
                                   num_inference_steps=steps, generator=generator).images[0]
            self.busy = False
            return image_name
        except Exception as e:
            self.busy = False
            error_message = f"Произошла ошибка: {e}"
            logger.logging(error_message, color=Color.RED)
            raise Exception(error_message)


class Text2ImageAPI:

    def __init__(self, url):
        try:
            self.URL = url
            self.AUTH_HEADERS = {
                'X-Key': f'Key {api_key}',
                'X-Secret': f'Secret {secret_key}',
            }
        except Exception as e:
            print("error in async_image:(id:4)", e)

    def get_model(self):
        try:
            response = requests.get(self.URL + 'key/api/v1/models', headers=self.AUTH_HEADERS)
            data = response.json()
            return data[0]['id']
        except Exception as e:
            print("error in async_image:(id:3)", e)

    def generate(self, prompt, negative_prompt, model, images=1, width=1024, height=1024, style="UHD"):
        try:
            params = {
                "type": "GENERATE",
                "style": style,
                "numImages": images,
                "negativePromptUnclip": negative_prompt,
                "width": width,
                "height": height,
                "generateParams": {
                    "query": f"{prompt}"
                }
            }

            data = {
                'model_id': (None, model),
                'params': (None, json.dumps(params), 'application/json')
            }
            response = requests.post(self.URL + 'key/api/v1/text2image/run', headers=self.AUTH_HEADERS, files=data)
            data = response.json()
            return data['uuid']
        except Exception as e:
            print("error in async_image:(id:2)", e)

    def check_generation(self, request_id, attempts=10, delay=1):
        try:
            while attempts > 0:
                response = requests.get(self.URL + 'key/api/v1/text2image/status/' + request_id,
                                        headers=self.AUTH_HEADERS)
                data = response.json()
                if data['status'] == 'DONE':
                    return data['images']

                attempts -= 1
                time.sleep(delay)
        except Exception as e:
            print("error in async_image:(id:1)", e)


async def convert_mp4_to_gif(input_file, output_file, fps):
    video = VideoFileClip(input_file)
    video.write_gif(output_file, fps=fps)
    video.close()


async def upscale_image(cuda_number, image_path, prompt):
    import torch

    # load model and scheduler
    model_id = "stabilityai/stable-diffusion-x4-upscaler"
    pipeline = StableDiffusionUpscalePipeline.from_pretrained(
        model_id, revision="fp16", torch_dtype=torch.float16
    )
    pipeline = pipeline.to(f"cuda:{cuda_number}")

    upscaled_image = pipeline(prompt=prompt, image=image_path).images[0]
    upscaled_image.save(image_path)


async def video_generate(image_path, seed, fps, decode_chunk_size=8):
    import torch

    video_path = image_path.replace(".png", ".mp4")

    pipe = StableVideoDiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid-xt", torch_dtype=torch.float16, variant="fp16"
    )
    pipe.enable_model_cpu_offload()

    # Load the conditioning image
    scale_image(image_path=image_path, max_size=1024 * 1024)
    image = Image.open(image_path)

    generator = torch.manual_seed(seed)
    frames = pipe(image, decode_chunk_size=decode_chunk_size, generator=generator).frames[0]

    export_to_video(frames, video_path, fps=fps)
    await convert_mp4_to_gif(video_path, video_path.replace(".mp4", ".gif"), fps)


async def audio_generate(cuda_number, wav_audio_path, prompt, duration, steps):
    import torch

    repo_id = "ucsd-reach/musicldm"
    pipe = MusicLDMPipeline.from_pretrained(repo_id, torch_dtype=torch.float16)
    pipe = pipe.to(f"cuda{cuda_number}")

    audio = pipe(prompt, num_inference_steps=steps, audio_length_in_s=duration).audios[0]

    # save the audio sample as a .wav file
    write(wav_audio_path, rate=16000, data=audio)
