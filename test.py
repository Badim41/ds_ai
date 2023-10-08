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
# FileLink(f'{os.path.basename(output_path)[:-4]}
import configparser


def utf_code(text):
    if type(text) == "list":
        text = ' '.join(text)
    with open("temp1", "w", encoding="cp1251") as file_utf8:
        file_utf8.write(text)
    with open("temp1", "r", encoding="cp1251") as file:
        return file.read()


config = configparser.ConfigParser()
config.read('config.ini')
currentAIname = config.get('Default', 'currentainame')
with open("caversAI/audio_links.txt", "w") as file:
    file.write(utf_code(currentAIname))
