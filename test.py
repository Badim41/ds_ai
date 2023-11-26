import sys

from scipy.io.wavfile import write as write_wav
from bark import SAMPLE_RATE, generate_audio, preload_models

if __name__ == "__main__":
    preload_models()
    arguments = sys.argv
    if len(arguments) > 3:
        text = arguments[2]
        speaker = arguments[3]
        audio_array = generate_audio(text, history_prompt=speaker)
        write_wav("audio.wav", SAMPLE_RATE, audio_array)