import numpy as np
import os
import subprocess

import nltk
from pydub import AudioSegment

from scipy.io.wavfile import write as write_wav
from scipy.io.wavfile import read as read_wav

import asyncio

from discord_tools.logs import Logs, Color

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = Logs(warnings=True)


async def merge_audio_files(input_paths, output_path):
    # Создаем список объектов AudioSegment для каждого входного аудиофайла
    audio_segments = [AudioSegment.from_file(path) for path in input_paths]

    # Соединяем все аудиофайлы
    merged_audio = sum(audio_segments)

    # Сохраняем результирующий аудиофайл
    merged_audio.export(output_path, format="mp3")

class BarkTTS():
    def __init__(self):
        self.activate_venv_cmd = f"venv_bark/bin/activate"
        self.started = False

        # Проверяем, установлены ли пакеты в виртуальное окружение, и если нет - устанавливаем их
        try:
            command = ". venv_bark/bin/activate && python -m bark -h"
            subprocess.run(command, shell=True, check=True)
        except:
            logger.logging("[bark] Create bark_venv", color=Color.GRAY)
            subprocess.run(["python", "-m", "venv", "venv_bark"], check=True)
            logger.logging("[bark] Installing packages", color=Color.GRAY)
            command = ". venv_bark/bin/activate && pip install git+https://github.com/suno-ai/bark.git nltk pydub"
            subprocess.run(command, shell=True, check=True)

        logger.logging("[bark] Ready to start", color=Color.GRAY)
        self.started = True

    async def text_to_speech_bark(self, text, speaker=1, audio_path="2.mp3", gen_temp=0.6):
        if not self.started:
            raise Exception("Загружается")
        file_name = audio_path[:audio_path.find(".mp3")]

        # Загрузка текста
        text = text.replace("\n", " ").strip()
        sentences = nltk.sent_tokenize(text)

        SAMPLE_RATE = 44000

        speaker = f"v2/ru_speaker_{speaker}"

        pieces = []
        for i, sentence in enumerate(sentences):
            temp_audio_file = f"{file_name}-temp{i}.wav"

            command = f". venv_bark/bin/activate && python -m bark --text \"{sentence}\" --output_filename \"{temp_audio_file}\" --history_prompt {speaker} --text_temp {gen_temp}"
            subprocess.run(command, shell=True, check=True)

            pieces.append(temp_audio_file)

        await merge_audio_files(input_paths=pieces, output_path=audio_path)