import asyncio
import json
import numpy as np
import os
import re
import subprocess
import traceback
from pydub import AudioSegment

from diffusers import KandinskyV22PriorEmb2EmbPipeline, KandinskyV22ControlnetImg2ImgPipeline
from diffusers.utils import load_image
from elevenlabs import generate, save, set_api_key, VoiceSettings, Voice
from gtts import gTTS
from transformers import pipeline

from cover_gen import run_ai_cover_gen
from discord_bot import DiscordUser, SQL_Keys, characters_all
from discord_tools.detect_mat import moderate_mat_in_sentence
from discord_tools.logs import Color, Logs
from discord_tools.secret import load_secret, SecretKey, create_secrets
from voice_change import Voice_Changer

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
                logger.logging(line,Color.CYAN)
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
                 protect=0.33, algo="rmvpe", speed=1, voice_model_eleven="Adam", stability=0.4,
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
        self.elevenlabs_voice_keys = load_secret(SecretKey.voice_keys)

    async def text_to_speech(self, text, audio_path="1.mp3", output_name=None):
        if text is None or text.replace("\n", "").replace(" ", "") == "":
            await logger.logging(f"Пустой текст \"{text}\"", Color.RED)
            raise "No text"
        mat_found, text = await moderate_mat_in_sentence(text)

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

        if len(text) > max_simbols:
            await logger.logging("gtts", text, color=Color.YELLOW)
            await self.gtts(text, audio_file, language="ru")
            pitch -= 12
        else:
            # получаем ключ для elevenlab
            key = self.elevenlabs_voice_keys[0]
            if not key == "Free":
                set_api_key(key)

            try:
                voice_id = await self.get_elevenlabs_voice_id_by_name()
                logger.logging("VOICE_ID_ELEVENLABS:", voice_id, Color.GRAY)
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
                pitch = await self.elevenlabs_text_to_speech(text, audio_file)
        return pitch

    async def gtts(self, tts, output_file, language="ru"):
        voiceFile = gTTS(tts, lang=language)
        voiceFile.save(output_file)

    async def voice_changer(self, input_path, output_path, pitch_change):
        audio_path = self.voice_RVC.voice_change(input_path, output_path, pitch_change=pitch_change)
        await logger.logging("done RVC", Color.GREEN)
        await speed_up_audio(audio_path, self.speed)
        return audio_path

    async def get_elevenlabs_voice_id_by_name(self):
        with open('voices.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
        voice = next((v for v in data["voices"] if v["name"] == self.voice_name), None)
        return voice["voice_id"] if voice else None


class Character:
    def __init__(self, name, max_simbols=300, algo="rmwpe", protect=0.2, rms_mix_rate=0.3, index_rate=0.5,
                 filter_radius=3, speaker_boost=True):
        if name in characters_all.items():
            existing_character = characters_all[name]
            self.__dict__.update(existing_character.__dict__)
        else:

            characters_all[name] = self

            self.name = name
            if name is None:
                self.gpt_info = "Вы полезный ассистент и даёте только полезную информацию"
            else:
                json_file_path = os.path.join(f'rvc_models', name, "params.json")
                with open(json_file_path, 'r') as json_file:
                    json_data = json.load(json_file)
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

                self.speed = int(json_data["speed"])
                self.voice_model_eleven = json_data["voice_model_eleven"]
                self.stability = float(json_data["stability"])
                self.similarity_boost = float(json_data["similarity_boost"])
                self.style = float(json_data["style"])
                self.max_simbols = max_simbols

                if algo.lower() not in ["mangio-crepe", "rmvpe"]:
                    raise "Not found algo"
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

        has_only_old_params = (index_rate is None and pitch is None and filter_radius is None and
                      rms_mix_rate is None and protect is None and algo is None and speed is None and
                      voice_model_eleven is None and stability is None and similarity_boost is None and
                      style is None and max_simbols is None and speaker_boost is None)

        if index_rate is None:
            index_rate = self.index_rate
        if pitch is None:
            pitch = self.pitch
        if filter_radius is None:
            filter_radius = self.filter_radius
        if rms_mix_rate is None:
            rms_mix_rate = self.rms_mix_rate
        if protect is None:
            protect = self.protect
        if algo is None:
            algo = self.algo
        if speed is None:
            speed = self.speed
        if voice_model_eleven is None:
            voice_model_eleven = self.voice_model_eleven
        if stability is None:
            stability = self.stability
        if similarity_boost is None:
            similarity_boost = self.similarity_boost
        if style is None:
            style = self.style
        if max_simbols is None:
            max_simbols = self.max_simbols
        if speaker_boost is None:
            speaker_boost = self.speaker_boost

        if not self.voice or not has_only_old_params:
            self.voice = TextToSpeechRVC(cuda_number=cuda_number, voice_name=self.name, index_rate=index_rate,
                                         pitch=pitch, filter_radius=filter_radius,
                                         rms_mix_rate=rms_mix_rate, protect=protect, algo=algo, speed=speed,
                                         voice_model_eleven=voice_model_eleven, stability=stability,
                                         similarity_boost=similarity_boost, style=style, max_simbols=max_simbols,
                                         speaker_boost=speaker_boost)
            logger.logging(f"Updated {self.name} params", Color.CYAN)

    async def text_to_speech(self, text, audio_path="1.mp3", output_name="2.mp3"):
        if not self.voice:
            self.voice = self.load_voice(0)
        await self.voice.text_to_speech(text, audio_path=audio_path, output_name=output_name)


class Image_Generator:
    def __init__(self, cuda_index):
        cuda_number = str(cuda_index)
        os.environ["CUDA_VISIBLE_DEVICES"] = cuda_number
        import torch
        self.torch = torch
        self.cuda_index = cuda_index
        self.pipe_prior = None
        self.pipe = None
        self.load_models()
        self.loaded = False
        self.busy = False

    def load_models(self):
        try:
            logger.logging(f"image model loading... GPU:{self.cuda_index}", Color.GRAY)
            self.pipe_prior = KandinskyV22PriorEmb2EmbPipeline.from_pretrained(
                "kandinsky-community/kandinsky-2-2-prior", torch_dtype=self.torch.float16
            )

            self.pipe = KandinskyV22ControlnetImg2ImgPipeline.from_pretrained(
                "kandinsky-community/kandinsky-2-2-controlnet-depth", torch_dtype=self.torch.float16
            )

            logger.logging(f"==========Images Model Loaded{self.cuda_index}!==========", Color.GRAY)
            self.loaded = True
        except Exception as e:
            logger.logging(f"Error while loading models: {e}", Color.RED)

    async def generate_image(self, prompt, negative_prompt, x, y, steps, seed, strength, strength_prompt,
                             strength_negative_prompt, image_name):
        if not self.loaded:
            raise "Модель не загружена"
        if self.busy:
            await logger.logging("warn: Модель занята", Color.YELLOW)
            await asyncio.sleep(0.25)
        self.busy = True
        try:
            def make_hint(image, depth_estimator):
                image = depth_estimator(image)["depth"]
                image = np.array(image)
                image = image[:, :, None]
                image = np.concatenate([image, image, image], axis=2)
                detected_map = self.torch.from_numpy(image).float() / 255.0
                hint = detected_map.permute(2, 0, 1)
                return hint

            # create generator
            generator = self.torch.Generator(device="cuda").manual_seed(seed)

            # make hint
            img = load_image(image_name).resize((x, y))
            depth_estimator = pipeline("depth-estimation")
            hint = make_hint(img, depth_estimator).unsqueeze(0).half().to("cuda:0")

            # run prior pipeline
            img_emb = self.pipe_prior(prompt=prompt, image=img, strength=strength_prompt,
                                      generator=generator)
            negative_emb = self.pipe_prior(prompt=negative_prompt, image=img,
                                           strength=strength_negative_prompt,
                                           generator=generator)

            # run controlnet img2img pipeline
            images = self.pipe(
                image=img,
                strength=strength,
                image_embeds=img_emb.image_embeds,
                negative_image_embeds=negative_emb.image_embeds,
                hint=hint,
                num_inference_steps=steps,
                generator=generator,
                height=y,
                width=x,
            ).images

            images[0].save(image_name)
            self.busy = False
            return image_name
        except Exception as e:
            self.busy = False
            error_message = f"Произошла ошибка: {e}"
            return error_message


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
