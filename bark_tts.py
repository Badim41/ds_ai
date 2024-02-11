import os
import subprocess
from discord_tools.logs import Logs, Color

BASE_DIR = os.path.basename(os.path.abspath(__file__))

logger = Logs(warnings=True)


class BarkTTS():
    def __init__(self):
        self.activate_venv_cmd = f"{BASE_DIR}/venv_bark/bin/activate"

        # Проверяем, установлены ли пакеты в виртуальное окружение, и если нет - устанавливаем их
        if not os.path.exists(f"{BASE_DIR}/venv_bark/bin/activate"):
            logger.logging("[bark] Create bark_venv", color=Color.GRAY)
            subprocess.run(["python", "-m", "venv", "venv_bark"], check=True)
            logger.logging("[bark] Installing packages", color=Color.GRAY)
            subprocess.run(
                [f". {self.activate_venv_cmd} && pip install git+https://github.com/suno-ai/bark.git nltk pydub"],
                shell=True, check=True)
        self.load_imports()
        logger.logging("[bark] Preload models", color=Color.GRAY)
        bark_generation = __import__('bark.generation', globals(), locals(), ['preload_models'], 0)
        bark_generation.preload_models()
        logger.logging("[bark] Ready to start", color=Color.GRAY)
        self.started = True

    def load_imports(self):
        # Активируем виртуальное окружение
        activate_command = f'. {self.activate_venv_cmd}'
        activate_process = subprocess.Popen(activate_command, shell=True, stdin=subprocess.PIPE)

        # Импортируем модуль после активации виртуального окружения
        imports = """
from bark.generation import preload_models
import numpy as np
from pydub import AudioSegment
import nltk
from bark import SAMPLE_RATE
from bark.api import semantic_to_waveform
from bark.generation import generate_text_semantic
from scipy.io.wavfile import write as write_wav
"""
        activate_process.stdin.write(imports.encode())
        activate_process.stdin.close()
        activate_process.wait()

    async def text_to_speech_bark(self, text, speaker, audio_path="2.mp3", gen_temp=0.6):
        if not self.started:
            raise Exception("Загружается")
        self.load_imports()
        # Импорт необходимых модулей
        nltk_module = __import__('nltk', globals(), locals(), [], 0)
        np_module = __import__('numpy', globals(), locals(), [], 0)
        bark_module = __import__('bark', globals(), locals(), ['SAMPLE_RATE'], 0)
        generate_text_semantic = __import__('bark.generation', globals(), locals(), ['generate_text_semantic'],
                                            0).generate_text_semantic
        write_wav = __import__('scipy.io.wavfile', globals(), locals(), ['write'], 0).write
        AudioSegment = __import__('pydub', globals(), locals(), ['AudioSegment'], 0).AudioSegment

        # Загрузка текста
        text = text.replace("\n", " ").strip()
        sentences = nltk_module.sent_tokenize(text)

        silence = np_module.zeros(int(0.1 * bark_module.SAMPLE_RATE))

        pieces = []
        for sentence in sentences:
            print("Sentence:", sentence)
            semantic_tokens = generate_text_semantic(
                sentence,
                history_prompt=f"v2/ru_speaker_{speaker}",
                temp=gen_temp,
                min_eos_p=0.05,  # this controls how likely the generation is to end
            )

            audio_array = bark_module.semantic_to_waveform(semantic_tokens, history_prompt=speaker)
            pieces += [audio_array, silence.copy()]

        # Объединение аудиофрагментов
        audio_result = np_module.concatenate(pieces)

        # Нормализация аудио до 16-бит
        audio_result = (audio_result / np_module.max(np_module.abs(audio_result)) * 32767).astype(np_module.int16)

        # Сохранение в WAV
        wav_audio_path = audio_path.replace(".mp3", "wav")
        write_wav(wav_audio_path, bark_module.SAMPLE_RATE, audio_result)

        # Преобразование в MP3
        audio = AudioSegment.from_wav(wav_audio_path)
        audio.export(audio_path, format="mp3")

        # Удаление временного WAV файла
        os.remove(wav_audio_path)