import librosa
import soundfile as sf

from pydub import AudioSegment
speed_factor = 0.5
input_file = "C:\\Users\\as280\\Downloads\\Vozhatye_-_YA_vozhatyjj_ty_vozhatyjj_63579162.mp3"
y, sr = librosa.load(input_file)

# Замедление аудио
y_slowed = librosa.effects.time_stretch(y, 0.75)  # Укажите желаемый коэффициент замедления

# Сохранение замедленного аудиофайла
output_path = 'путь_к_вашему_выходному_аудиофайлу.wav'
sf.write(input_file, y_slowed, sr)