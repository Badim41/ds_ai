# import os
# import zipfile
#
# from IPython.lib.display import FileLink
#
# print("test")
# output_path = "B:/AICoverGen/AICoverGen/song_output/path4.txt"
# audio_paths = ["B:/AICoverGen/AICoverGen/song_output/path1.txt", "B:/AICoverGen/AICoverGen/song_output/path2.txt",
#                "B:/AICoverGen/AICoverGen/song_output/path3.txt"]
# with zipfile.ZipFile(f'{os.path.basename(output_path)[:-4]}.zip', 'w') as zipf:
#     zipf.write(audio_paths[0], arcname='вокал.mp3')
#     zipf.write(audio_paths[1], arcname='бэквокал.mp3')
#     zipf.write(audio_paths[2], arcname='музыка.mp3')
# FileLink(f'{os.path.basename(output_path)[:-4]}.zip')
from pydub import AudioSegment

# Создайте пустой аудиофайл длительностью 0 миллисекунд
empty_audio = AudioSegment.silent(duration=0)
mp3_filename = 'empty.mp3'
empty_audio.export(mp3_filename, format="mp3")

print(f'Создан пустой файл {mp3_filename}.')