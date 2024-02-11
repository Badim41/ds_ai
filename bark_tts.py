import numpy as np
import os
import subprocess

import nltk
from pydub import AudioSegment

from scipy.io.wavfile import write as write_wav
from scipy.io.wavfile import read as read_wav

from discord_tools.logs import Logs, Color

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logger = Logs(warnings=True)


class BarkTTS():
    def __init__(self):
        self.activate_venv_cmd = f". {BASE_DIR}/venv_bark/bin/activate && "
        self.started = False

        # Проверяем, установлены ли пакеты в виртуальное окружение, и если нет - устанавливаем их
        if not os.path.exists(f"{BASE_DIR}/venv_bark/bin/activate"):
            logger.logging("[bark] Create bark_venv", color=Color.GRAY)
            subprocess.run(["python", "-m", "venv", "venv_bark"], check=True)
            logger.logging("[bark] Installing packages", color=Color.GRAY)
            install_process = subprocess.Popen(
                [self.activate_venv_cmd, "pip", "install", "git+https://github.com/suno-ai/bark.git", "nltk", "pydub"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            install_output, install_error = install_process.communicate()
            if install_process.returncode != 0:
                raise Exception(f"Ошибка при установке пакетов: {install_error.decode()}")
        logger.logging("[bark] Preload models", color=Color.GRAY)
        subprocess.run(f"{self.activate_venv_cmd}python -m bark --text \"test\" --output_filename \"test.wav\"",
                       check=True)
        logger.logging("[bark] Ready to start", color=Color.GRAY)
        self.started = True

    async def text_to_speech_bark(self, text, speaker, audio_path="2.mp3", gen_temp=0.6):
        if not self.started:
            raise Exception("Загружается")

        # Загрузка текста
        text = text.replace("\n", " ").strip()
        sentences = nltk.sent_tokenize(text)

        SAMPLE_RATE = 44000

        speaker = f"v2/ru_speaker_{speaker}"

        pieces = []
        for sentence in sentences:
            # Создание аудиофайла из предложения
            cmd = f"{self.activate_venv_cmd}python -m bark --text \"{sentence}\" --output_filename \"temp.wav\" --history_prompt {speaker} --text_temp {gen_temp}"
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                raise Exception(
                    f"Произошла ошибка при выполнении команды: {cmd}\nСтандартный вывод: {stdout.decode('utf-8')}\nСтандартная ошибка: {stderr.decode('utf-8')}")

            # Преобразование аудиофайла в массив numpy
            audio_piece, _ = read_wav("temp.wav")
            pieces.append(audio_piece)

        # Объединение аудиофрагментов
        audio_result = np.vstack(pieces)

        # Нормализация аудио до 16-бит
        audio_result = (audio_result / np.max(np.abs(audio_result)) * 32767).astype(np.int16)

        # Сохранение в WAV
        wav_audio_path = audio_path.replace(".mp3", ".wav")
        write_wav(wav_audio_path, SAMPLE_RATE, audio_result)

        # Преобразование в MP3
        audio = AudioSegment.from_wav(wav_audio_path)
        audio.export(audio_path, format="mp3")

        # Удаление временного WAV файла
        os.remove(wav_audio_path)
