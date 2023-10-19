import json

# Загрузка данных из JSON файла
with open('cookies.json', 'r') as file:
    cookie_data = json.load(file)

# Преобразование данных в формат, подходящий для cookie
cookies = {key: value for key, value in cookie_data.items()}

# Пример использования
print(cookies)