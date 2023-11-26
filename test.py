import os

# Получаем текущую директорию
current_directory = os.getcwd()

# Получаем список файлов в текущей директории
files = os.listdir(current_directory)

# Фильтруем файлы по расширению .py и выводим их имена
python_files = [file for file in files if file.endswith('.py')]
for file in python_files:
    print(file)
