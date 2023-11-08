import os
import sys
import zipfile
import shutil
import requests

BASE_DIR = os.getcwd()
rvc_models_dir = os.path.join(BASE_DIR, 'rvc_models')


def extract_zip(extraction_folder, zip_name):
    os.makedirs(extraction_folder)
    with zipfile.ZipFile(zip_name, 'r') as zip_ref:
        zip_ref.extractall(extraction_folder)
    os.remove(zip_name)

    index_filepath, model_filepath = None, None
    for root, dirs, files in os.walk(extraction_folder):
        for name in files:
            if name.endswith('.index') and os.stat(os.path.join(root, name)).st_size > 1024 * 100:
                index_filepath = os.path.join(root, name)

            if name.endswith('.pth') and os.stat(os.path.join(root, name)).st_size > 1024 * 1024 * 40:
                model_filepath = os.path.join(root, name)

    if not model_filepath:
        raise Exception(f'Нет .pth файла в zip. архиву. Проверьте {extraction_folder}.')
    # move model and index file to extraction folder
    os.rename(model_filepath, os.path.join(extraction_folder, os.path.basename(model_filepath)))
    if index_filepath:
        os.rename(index_filepath, os.path.join(extraction_folder, os.path.basename(index_filepath)))

    # remove any unnecessary nested folders
    for filepath in os.listdir(extraction_folder):
        if os.path.isdir(os.path.join(extraction_folder, filepath)):
            shutil.rmtree(os.path.join(extraction_folder, filepath))


def download_online_model(url, dir_name, gender, info, speed, voice_model):
    try:
        print(f'[~] Скачивание модели с именем {dir_name}...')
        zip_name = url.split('/')[-1]
        extraction_folder = os.path.join(rvc_models_dir, dir_name)
        with open(os.path.join(extraction_folder + "/info.txt"), 'w') as writer:
            writer.writelines(info)
        with open(os.path.join(extraction_folder + "/gender.txt"), 'w') as writer:
            writer.writelines(gender)
        with open(os.path.join(extraction_folder + "/speed.txt"), 'w') as writer:
            writer.writelines(str(speed))
        with open(f"rvc_models/{dir_name_input}/voice_model.txt", "w") as writer:
            writer.write(dir_name_input)
        if os.path.exists(extraction_folder):
            raise Exception \
                (f'Модель {dir_name} уже существует, но её информация/скорость были изменены')


        if 'pixeldrain.com' in url:
            url = f'https://pixeldrain.com/api/file/{zip_name}'

        response = requests.get(url, stream=True)
        with open(zip_name, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        print('[~] Разархивация...')
        extract_zip(extraction_folder, zip_name)
        print(f'[+] {dir_name} модель успешно установлена!')

    except Exception as e:
        raise Exception(str(e))


arguments = sys.argv
if len(arguments) > 6:
    url_input = arguments[1]
    dir_name_input = arguments[2]
    gender = arguments[3]
    info = "Вот информация о тебе:" + arguments[4]
    voice_model = arguments[5]
    speed = float(arguments[6])
    if speed is None or speed < 0 or speed > 2:
        speed = 1
    download_online_model(url_input, dir_name_input, gender, info, speed, voice_model)
else:
    print("Нужно указать ссылку и имя модели")
    exit(-1)
