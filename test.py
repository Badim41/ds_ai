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
import http.server
import socketserver
import zipfile

# Создание .zip архива
zip_filename = 'архив.zip'
with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('test.py', arcname='test.py')

# Настройка HTTP сервера
port = 8080
Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", port), Handler) as httpd:
    print(f"Сервер работает на порту {port}")
    print(f"Вы можете скачать архив по адресу: http://localhost:{port}/{zip_filename}")
    httpd.serve_forever()