import asyncio
import datetime
import multiprocessing
import random
import shutil
import subprocess
import time
from PIL import Image
from moviepy.editor import VideoFileClip, AudioFileClip
import configparser
import imageio
import os

config = configparser.ConfigParser()


async def set_get_config_all(section, key, value):
    config.read('config.ini')
    if value is None:
        return config.get(section, key)
    config.set(section, key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def set_get_config_all_not_async(section, key, value):
    config.read('config.ini')
    if value is None:
        return config.get(section, key)
    config.set(section, key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def image_change(index, output_folder, prompt):
    # 1 GPU
    if index is None:
        print("image changing...")
        for filename in sorted(os.listdir(output_folder)):
            if filename.endswith('.png'):
                print("changing...", filename)
                set_get_config_all_not_async(f"Image1", "result", "None")
                set_get_config_all_not_async(f"Image1", "input", "frames/" + filename)
                set_get_config_all_not_async(f"Image1", "prompt", prompt)
                # wait for answer
                while True:
                    if not set_get_config_all_not_async(f"Image1", "result", None) == "None":
                        break
                    time.sleep(0.25)
        set_get_config_all_not_async(f"Video1", "result", True)
        return
    # 2 GPU
    i = 0
    print("image changing...")
    for filename in sorted(os.listdir(output_folder)):
        if filename.endswith('.png'):
            i += 1
            if i % 2 == index:
                print("changing...", filename)
                set_get_config_all_not_async(f"Image{index + 1}", "result", "None")
                set_get_config_all_not_async(f"Image{index + 1}", "input", "frames/" + filename)
                set_get_config_all_not_async(f"Image{index + 1}", "prompt", prompt)
                # wait for answer
                while True:
                    if not set_get_config_all_not_async(f"Image{index + 1}", "result", None) == "None":
                        break
                    time.sleep(0.25)
    set_get_config_all_not_async(f"Video{index + 1}", "result", True)


async def video_pipeline(video_path, fps_output, video_extension, prompt, voice,
                         pitch, indexrate, loudness, main_vocal, back_vocal,
                         music, roomsize, wetness, dryness):
    try:
        start_time = datetime.datetime.now()
        current_time = start_time.time()
        print("Начало:", current_time)

        # === разбиваем видео на карды ===
        output_folder = 'frames'
        os.makedirs(output_folder, exist_ok=True)
        video_id = str(random.randint(1, 1000000))

        # считаем FPS
        video_clip = VideoFileClip(video_path)
        original_fps = video_clip.fps
        print(original_fps)

        # Извлекаем аудио
        extracted_audio_path = video_id + ".mp3"
        video_clip = VideoFileClip(video_path)
        audio_clip = video_clip.audio
        audio_clip.write_audiofile(extracted_audio_path)

        # Размер
        # 480p=640×480
        # 360p=480×360
        # 240p=426×240
        # 144p=256×144
        new_width = None
        new_height = None
        if video_extension == "480p":
            new_width = 640
            new_height = 512
        elif video_extension == "360p":
            new_width = 512
            new_height = 384
        elif video_extension == "240p":
            new_width = 448
            new_height = 256
        elif video_extension == "144p":
            new_width = 256
            new_height = 128
        old_width = None
        old_height = None
        if video_extension == "480p":
            old_width = 640
            old_height = 480
        elif video_extension == "360p":
            old_width = 480
            old_height = 360
        elif video_extension == "240p":
            old_width = 426
            old_height = 240
        elif video_extension == "144p":
            old_width = 256
            old_height = 144

        # пропуск изображений (установка FPS)
        save_img_step = original_fps / fps_output

        frame_number = 0
        video_clip = VideoFileClip(video_path)
        for frame in video_clip.iter_frames(fps=original_fps):
            frame_number += 1
            if not frame_number % save_img_step == 0:
                continue
            frame_image = Image.fromarray(frame)
            frame_image = frame_image.resize((new_width, new_height))
            frame_filename = os.path.join(output_folder, f'{frame_number:09d}.png')
            frame_image.save(frame_filename)
        print(f"saved {frame_number // save_img_step} frames!")

        # === обработка изображений ===
        if await set_get_config_all("Image2", "model_loaded", None) == "True":
            # 2 GPU
            await set_get_config_all(f"Video1", "result", False)
            await set_get_config_all(f"Video2", "result", False)
            pool1 = multiprocessing.Pool(processes=1)
            pool1.apply_async(image_change(0, output_folder, prompt, ))
            pool1.close()
            pool2 = multiprocessing.Pool(processes=1)
            pool2.apply_async(image_change(1, output_folder, prompt, ))
            pool2.close()
            # wait for results
            while True:
                continue1 = await set_get_config_all(f"Video1", "result", None) == "True"
                continue2 = await set_get_config_all(f"Video2", "result", None) == "True"
                if continue1 and continue2:
                    break
                await asyncio.sleep(10)
        else:
            # 1 GPU
            await set_get_config_all(f"Video1", "result", False)
            pool1 = multiprocessing.Pool(processes=1)
            pool1.apply_async(image_change(None, output_folder, prompt, ))
            pool1.close()
            # wait for results
            while True:
                continue1 = await set_get_config_all(f"Video1", "result", None) == "True"
                if continue1:
                    break
                await asyncio.sleep(10)

        # === обработка звука ===
        if not voice == "None":
            await set_get_config_all("voice", "generated", "None")
            command = [
                "python",
                "src/main.py",
                "-i", extracted_audio_path,
                "-dir", voice,
                "-p", str(pitch),
                "-ir", str(indexrate),
                "-fr", str(loudness),
                "-mv", str(main_vocal),
                "-bv", str(back_vocal),
                "-iv", str(music),
                "-rsize", str(roomsize),
                "-rwet", str(wetness),
                "-rdry", str(dryness)
            ]
            subprocess.run(command, check=True)

            # wait for result
            while True:
                audio_path = await set_get_config_all('voice', 'generated', None)
                if not audio_path == "None":
                    break
                time.sleep(2.5)
        else:
            audio_path = extracted_audio_path

        # === Снова создаём видео ===
        images = []
        for filename in sorted(os.listdir(output_folder)):
            if filename.endswith('.png'):
                # изменяем размер под нужное расширение
                image = Image.open(os.path.join(output_folder, filename))
                resized_image = image.resize((old_width, old_height))
                # добавляем кадр
                images.append(resized_image)
        output_video_path = video_id + '.mp4'

        # Создание видео
        print(int(original_fps / save_img_step))
        imageio.mimsave(output_video_path, images, fps=int(original_fps / save_img_step))

        # добавление звука
        video_name_with_sound = video_id + "_with_sound" + ".mp4"
        video_clip = VideoFileClip(output_video_path)
        video_clip = video_clip.set_audio(AudioFileClip(audio_path))
        video_clip.write_videofile(video_name_with_sound, codec='libx264')

        end_time = datetime.datetime.now()
        current_time = end_time.time()
        print("Конец:", current_time)

        # подсчёт времени
        spent_time = end_time - start_time
        print("Прошло времени:", spent_time)
        await set_get_config_all("Image1", "spent_time", spent_time)
        await set_get_config_all("Image2", "spent_time", spent_time)

        # удаление временных файлов
        os.remove(video_path)
        os.remove(output_video_path)
        os.remove(extracted_audio_path)
        shutil.rmtree(output_folder)
        return video_name_with_sound
    except Exception as e:
        print(f"Произошла ошибка: {e}")

    return None
