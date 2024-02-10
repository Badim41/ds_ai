import numpy as np
from pydub import AudioSegment

import nltk
from bark import SAMPLE_RATE
from bark.api import semantic_to_waveform
from bark.generation import (
    generate_text_semantic,
    preload_models
)
from scipy.io.wavfile import write as write_wav

preload_models()

script = """
Hey, have you heard about this new text-to-audio model called "Bark"? 
Apparently, it's the most realistic and natural-sounding text-to-audio model 
out there right now. People are saying it sounds just like a real person speaking. 
I think it uses advanced machine learning algorithms to analyze and understand the 
nuances of human speech, and then replicates those nuances in its own speech output. 
It's pretty impressive, and I bet it could be used for things like audiobooks or podcasts. 
In fact, I heard that some publishers are already starting to use Bark to create audiobooks. 
It would be like having your own personal voiceover artist. I really think Bark is going to 
be a game-changer in the world of text-to-audio technology.
""".replace("\n", " ").strip()

sentences = nltk.sent_tokenize(script)

GEN_TEMP = 0.6
SPEAKER = "v2/ru_speaker_2"
silence = np.zeros(int(0.25 * SAMPLE_RATE))  # quarter second of silence

pieces = []
for sentence in sentences:
    semantic_tokens = generate_text_semantic(
        sentence,
        history_prompt=SPEAKER,
        temp=GEN_TEMP,
        min_eos_p=0.05,  # this controls how likely the generation is to end
    )

    audio_array = semantic_to_waveform(semantic_tokens, history_prompt=SPEAKER,)
    pieces += [audio_array, silence.copy()]

# Concatenate audio pieces
audio_result = np.concatenate(pieces)

# Нормализация аудио до 16-бит
audio_result = (audio_result / np.max(np.abs(audio_result)) * 32767).astype(np.int16)
file_name = "result.wav"
# Сохранение
write_wav(file_name, SAMPLE_RATE, audio_result)

audio = AudioSegment.from_wav(file_name)
audio.export("1.mp3", format="mp3")
