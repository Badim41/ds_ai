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


async def merge_audio_files(file_main, file_secondary):
    # Загрузка аудиофайлов
    audio1 = AudioSegment.from_file(file_main)
    audio2 = AudioSegment.from_file(file_secondary)

    # Соединение аудиофайлов
    merged_audio = audio1 + audio2

    # Сохранение результирующего аудиофайла
    merged_audio.export(file_main, format="wav")
    os.remove(file_secondary)

class BarkTTS():
    def __init__(self):
        self.activate_venv_cmd = f"venv_bark/bin/activate"
        self.started = False

        # Проверяем, установлены ли пакеты в виртуальное окружение, и если нет - устанавливаем их
        if not os.path.exists(f"venv_bark/bin/activate"):
            logger.logging("[bark] Create bark_venv", color=Color.GRAY)
            subprocess.run(["python", "-m", "venv", "venv_bark"], check=True)
            logger.logging("[bark] Installing packages", color=Color.GRAY)
            command = ". venv_bark/bin/activate && pip install git+https://github.com/suno-ai/bark.git nltk pydub"
            subprocess.run(command, shell=True, check=True)

        try:
            self.started = True
            asyncio.run(self.text_to_speech_bark("а", audio_path="temp.mp3"))
        except Exception as e:
            self.started = False
            raise e
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
            # Создание аудиофайла из предложения
            temp_audio_file = f"{file_name}-temp{i}.wav"
            command = f". venv_bark/bin/activate && python -m bark --text \"{sentence}\" --output_filename \"{temp_audio_file}\" --history_prompt {speaker} --text_temp {gen_temp}"
            subprocess.run(command, shell=True, check=True)
            # Преобразование аудиофайла в массив numpy
            audio_piece, _ = read_wav(temp_audio_file)
            pieces.append(audio_piece)

        audio_result = np.vstack(pieces)

        # Нормализация аудио до 16-бит
        audio_result = (audio_result / np.max(np.abs(audio_result)) * 32767).astype(np.int16)

        # Сохранение в WAV
        wav_audio_path = audio_path.replace(".mp3", ".wav")
        write_wav(wav_audio_path, SAMPLE_RATE, audio_result)

        # Преобразование в MP3
        audio = AudioSegment.from_wav(wav_audio_path)
        audio.export(audio_path, format="mp3")