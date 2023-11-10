import os

import librosa
import pyrubberband as pyrb
import soundfile as sf

speed_factor = 0.5
input_file = "C:\\Users\\as280\\Downloads\\366374 (Фарадей Ver).mp3"
y, sr = librosa.load(input_file)
sr_new = 22050
y_resampled = librosa.resample(y, sr, sr_new)
y_slowed = librosa.effects.time_stretch(y_resampled, rate=speed_factor)
output_dir = os.path.dirname(input_file)
sf.write(output_dir + "output1.mp3", y_slowed, sr_new)

y, sr = sf.read(input_file)
y_stretch = pyrb.time_stretch(y, sr, speed_factor)
sf.write(output_dir + "output2.mp3", y_stretch, sr)
