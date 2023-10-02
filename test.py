import ffmpeg
from pydub import AudioSegment

# Загрузите ваши mp3 файлы
audio1 = AudioSegment.from_mp3(r"C:\Users\as280\Downloads\rawData4 [vocals].wav")
audio2 = AudioSegment.from_mp3(r"C:\Users\as280\Downloads\rawData4 [vocals].wav")

# Объедините аудиофайлы
combined_audio = audio1 + audio2

# Экспортируйте объединенное аудио в формате M4A
output_file = 'результирующий_файл.m4a'

# Преобразование AudioSegment в байты и сохранение во временный файл
temp_wav_file = 'temp.wav'
combined_audio.export(temp_wav_file, format='wav')

# Создание ffmpeg.Process для конвертации
ffmpeg.input(temp_wav_file, format='wav').output(output_file, format='ipod', acodec='aac').run(overwrite_output=True)

# Удаление временного WAV файла
import os
os.remove(temp_wav_file)

print("Конвертация завершена успешно.")
