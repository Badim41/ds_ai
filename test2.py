import re

with open(r"C:\Users\as280\Pictures\ds_ai\voice_download\all_voices.txt", "r", encoding="utf-8") as file:
    lines = file.readlines()
    lines[-1] = lines[-1] + " "
url = []
name = []
gender = []
info = []
speed = []
voice_model = []
for line in lines:
    if line.strip():
        # забейте, просто нужен пробел и всё
        line += ""
        line = line.replace(": ", ":")
        # /add_voice url:url_to_model name:some_name gender:мужчина info:some_info speed:some_speed voice_model:some_model
        pattern = r'(\w+):(.+?)\s(?=\w+:|$)'

        matches = re.findall(pattern, line)
        arguments = dict(matches)

        url.append(arguments.get('url', None))
        name.append(arguments.get('name', None))
        gender.append(arguments.get('gender', None))
        info.append(arguments.get('info', "Отсутствует"))
        speed.append(arguments.get('speed', "1"))
        voice_model.append(arguments.get('voice_model', "James"))

print(url)
print(name)
print(gender)