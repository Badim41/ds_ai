# import os
# from gtts import gTTS
#
# # from project_code_counter import list_python_files
#
# file_name = "1.mp3"
#
# if os.path.exists(file_name):
#     os.remove(file_name)
# # на вход идёт всегда русский текст, так что переводим его
# try:
#     voiceFile = gTTS('вот такое например', lang="ru")
#     # Сохранение в файл
#     voiceFile.save("1.mp3")
# except Exception as e:
#     print(f"Произошла ошибка при синтезе речи: {str(e)}")
string_input = ("123345333333333333333")
print(string_input[:2])