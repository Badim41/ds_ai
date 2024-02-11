import os
import subprocess
from discord_tools.logs import Logs, Color


BASE_DIR = os.getcwd()

logger = Logs(warnings=True)


class BarkTTS():
    def __init__(self):
        self.activate_venv_cmd = f"{BASE_DIR}/venv_bark/bin/activate"

        # Проверяем, установлены ли пакеты в виртуальное окружение, и если нет - устанавливаем их
        if not os.path.exists(f"{BASE_DIR}/venv_bark/bin/activate"):
            logger.logging("[bark] Create bark_venv", color=Color.GRAY)
            subprocess.run(["python -m venv venv_bark"], check=True)
            logger.logging("[bark] Installing packages", color=Color.GRAY)
            subprocess.run(
                [f". {self.activate_venv_cmd} && pip install git+https://github.com/suno-ai/bark.git nltk pydub"],
                shell=True, check=True)

        # Активируем виртуальное окружение
        activate_command = f'. {self.activate_venv_cmd}' if os.name == 'posix' else f'call {self.activate_venv_cmd}'
        subprocess.run(activate_command, shell=True, check=True)

        # Импортируем модуль после активации виртуального окружения
        from bark.generation import preload_models

        logger.logging("[bark] Preload models", color=Color.GRAY)
        preload_models()
        logger.logging("[bark] Ready to start", color=Color.GRAY)
        self.started = True

    async def text_to_speech_bark(self, text, speaker, audio_path="2.mp3", gen_temp=0.6):
        if not self.started:
            raise "Загружается"
        activate_command = f'. {self.activate_venv_cmd}' if os.name == 'posix' else f'call {self.activate_venv_cmd}'
        subprocess.run(activate_command, shell=True)
        import numpy as np
        from pydub import AudioSegment
        import nltk
        from bark import SAMPLE_RATE
        from bark.api import semantic_to_waveform
        from bark.generation import generate_text_semantic
        from scipy.io.wavfile import write as write_wav

        text = text.replace("\n", " ").strip()

        sentences = nltk.sent_tokenize(text)

        silence = np.zeros(int(0.1 * SAMPLE_RATE))

        pieces = []
        for sentence in sentences:
            print("Sentence:", sentence)
            semantic_tokens = generate_text_semantic(
                sentence,
                history_prompt=f"v2/ru_speaker_{speaker}",
                temp=gen_temp,
                min_eos_p=0.05,  # this controls how likely the generation is to end
            )

            audio_array = semantic_to_waveform(semantic_tokens, history_prompt=speaker, )
            pieces += [audio_array, silence.copy()]

        # Concatenate audio pieces
        audio_result = np.concatenate(pieces)

        # Нормализация аудио до 16-бит
        audio_result = (audio_result / np.max(np.abs(audio_result)) * 32767).astype(np.int16)

        # Сохранение
        wav_audio_path = audio_path.replace(".mp3", "wav")
        write_wav(wav_audio_path, SAMPLE_RATE, audio_result)

        # mp3
        audio = AudioSegment.from_wav(wav_audio_path)
        audio.export(audio_path, format="mp3")

        os.remove(wav_audio_path)
