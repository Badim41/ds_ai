import os

def list_python_files(root_dir):
    for foldername, subfolders, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                print(os.path.join(foldername, filename))
                with open(os.path.join(foldername, filename), "r") as reader:


# Замените 'путь/к/вашей/папке' на путь к вашей целевой директории
list_python_files('путь/к/вашей/папке')