import PIL
import asyncio
import base64
import gc
import json
import os
import re
import requests
import subprocess
import time
import traceback
from diffusers import Kandinsky3Img2ImgPipeline, StableDiffusionUpscalePipeline, StableVideoDiffusionPipeline, \
    MusicLDMPipeline, AutoPipelineForImage2Image, StableDiffusionPipeline, StableDiffusionLatentUpscalePipeline, \
    StableDiffusionXLImg2ImgPipeline, StableDiffusionXLInpaintPipeline
from diffusers.utils import export_to_video
from io import BytesIO
from moviepy.video.io.VideoFileClip import VideoFileClip
from pydub import AudioSegment
from scipy.io.wavfile import write
import torch
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


def convert_mp4_to_gif(input_file, output_file, fps):
    video = VideoFileClip(input_file)
    video.write_gif(output_file, fps=fps)
    video.close()


def get_image_dimensions(file_path):
    with Image.open(file_path) as img:
        width, height = img.size
    return int(width), int(height)


def scale_image_decorator(max_size=1024 * 1024, match_size=64):
    def decorator(func):
        def wrapper(*args, **kwargs):
            scale_image(image_path=kwargs.get("image_path"), max_size=max_size, match_size=match_size)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def scale_image(image_path, max_size, match_size=64):
    x, y = get_image_dimensions(image_path)

    # скэйлинг во избежания ошибок из-за нехватки памяти
    if max_size > x * y:
        scale_factor = (max_size / (x * y)) ** 0.5
        x = int(x * scale_factor)
        y = int(y * scale_factor)

    if not x % match_size == 0:
        x = ((x // match_size) + 1) * match_size
    if not y % match_size == 0:
        y = ((y // match_size) + 1) * match_size

    image = Image.open(image_path)
    resized_image = image.resize((x, y))
    resized_image.save(image_path)

    logger.logging(f"Resized: {x};{y}", color=Color.GRAY)




def invert_image(image_path):
    image = Image.open(image_path)
    inverted_image = Image.eval(image, lambda x: 255 - x)
    inverted_image.save(image_path)
    return Image.open(image_path)


def create_white_image(width, height):
    image = Image.new("RGB", (width, height), color="white")
    return image


def fill_transparent_with_black(image_path):
    image = Image.open(image_path)

    # имеет альфа-канал
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        # Создание нового изображения с фоном чёрного цвета
        new_image = Image.new('RGB', image.size, (0, 0, 0))
        new_image.paste(image, mask=image.split()[3])
        return new_image
    else:
        return image


async def generate_image_API(ctx, prompt, x, y, negative_prompt="", style="DEFAULT"):
    api = Text2ImageAPI('https://api-key.fusionbrain.ai/')
    model_id = api.get_model()

    if x and y:
        max_size = 1024 * 1024
        if max_size > x * y:
            scale_factor = (max_size / (x * y)) ** 0.5
            x = int(x * scale_factor)
            y = int(y * scale_factor)
    elif not x and not y:
        x, y = 1024, 1024
    else:
        await ctx.respond(f"Указана только 1 величина. X={x}, Y={y}")
        return

    uuid = api.generate(prompt=prompt, negative_prompt=negative_prompt, model=model_id, width=x, height=y,
                        style=style)
    image_data_base64 = api.check_generation(uuid)

    selected_image_base64 = image_data_base64[0]

    image_data_binary = base64.b64decode(selected_image_base64)

    input_image = "images/image" + str(ctx.author.id) + "_generate.png"

    with open(input_image, 'wb') as file:
        file.write(image_data_binary)
    return input_image


@scale_image_decorator(max_size=768 * 768, match_size=128)
async def inpaint_image(cuda_number, prompt, negative_prompt, image_path, mask_path,
                        invert, strength, steps, seed):
    try:
        image = Image.open(image_path)

        pipe = StableDiffusionXLInpaintPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
            variant="fp16",
            use_safetensors=True,
        )
        pipe = pipe.to(f"cuda:{cuda_number}")

        x, y = get_image_dimensions(image_path)

        if mask_path:
            # заполнение пустых пикселей чёрными
            mask = (fill_transparent_with_black(mask_path)).resize((x, y))
            if invert:
                # замена белых пикселей чёрными
                mask.save(mask_path)
                mask = invert_image(mask_path)
        else:
            # белое изображение
            mask = create_white_image(x, y)

        generator = torch.Generator(device=f"cuda:{cuda_number}").manual_seed(seed)

        pipe(prompt=prompt, image=image, mask_image=mask, num_inference_steps=steps, strength=strength,
             negative_prompt=negative_prompt, generator=generator).images[0].save(image_path)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        raise Exception(e)
    finally:
        del pipe
        torch.cuda.empty_cache()
        gc.collect()


@scale_image_decorator
async def refine_image(prompt, negative_prompt, strength, image_path, cuda_number, seed):
    try:
        image = Image.open(image_path)

        pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-refiner-1.0", torch_dtype=torch.float16
        )

        pipe = pipe.to(f"cuda:{cuda_number}")

        generator = torch.Generator(device=f"cuda:{cuda_number}").manual_seed(seed)

        pipe(prompt, image=image, generator=generator, negative_prompt=negative_prompt, strength=strength).images[
            0].save(image_path)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        raise Exception(e)
    finally:
        del pipe
        torch.cuda.empty_cache()
        gc.collect()


@scale_image_decorator
async def upscale_image(cuda_number, image_path, prompt, steps):
    try:
        model_id = "stabilityai/sd-x2-latent-upscaler"
        pipe = StableDiffusionLatentUpscalePipeline.from_pretrained(model_id, torch_dtype=torch.float16)
        pipe.to(f"cuda:{cuda_number}")

        if not prompt:
            prompt = "a photo of an astronaut high resolution, unreal engine, ultra realistic"

        generator = torch.Generator(device=f"cuda:{cuda_number}").manual_seed(33)

        image = Image.open(image_path)

        pipe(
            prompt=prompt,
            image=image,
            num_inference_steps=steps,
            guidance_scale=0,
            generator=generator,
        ).images[0].save(image_path)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        raise Exception(e)
    finally:
        del pipe
        torch.cuda.empty_cache()
        gc.collect()


@scale_image_decorator(max_size=768 * 768)
async def video_generate(image_path, seed, fps, decode_chunk_size=8):
    try:
        video_path = image_path.replace(".png", ".mp4")
        gif_path = video_path.replace(".mp4", ".gif")

        pipe = StableVideoDiffusionPipeline.from_pretrained(
            "stabilityai/stable-video-diffusion-img2vid-xt", torch_dtype=torch.float16, variant="fp16",
            device_map="balanced"
        )

        image = Image.open(image_path)

        generator = torch.manual_seed(seed)
        frames = pipe(image, decode_chunk_size=decode_chunk_size, generator=generator).frames[0]

        export_to_video(frames, video_path, fps=fps)
        convert_mp4_to_gif(video_path, gif_path, fps)
        return video_path, gif_path
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        raise Exception(e)
    finally:
        del pipe
        torch.cuda.empty_cache()
        gc.collect()


async def audio_generate(cuda_number, wav_audio_path, prompt, duration, steps):
    try:
        repo_id = "ucsd-reach/musicldm"
        pipe = MusicLDMPipeline.from_pretrained(repo_id, torch_dtype=torch.float16)
        pipe = pipe.to(f"cuda:{cuda_number}")

        audio = pipe(prompt, num_inference_steps=steps, audio_length_in_s=duration).audios[0]

        # save the audio sample as a .wav file
        write(wav_audio_path, rate=16000, data=audio)
    except Exception as e:
        traceback_str = traceback.format_exc()
        logger.logging(str(traceback_str), color=Color.RED)
        raise Exception(e)
    finally:
        del pipe
        torch.cuda.empty_cache()
        gc.collect()
