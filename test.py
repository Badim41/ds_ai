import asyncio
import datetime
import multiprocessing
import random
import shutil
import subprocess
import time

from PIL import Image
import imageio
import os

from moviepy.editor import VideoFileClip, AudioFileClip

try:
    start_time = datetime.datetime.now()
    current_time = start_time.time()
    print("Начало:", current_time)

    video_path = "C:/Users/as280/Downloads/Ты думал что-то здесь будет_.mp4"
    video_extension = "480p"
    fps_output = 60

    # === разбиваем видео на кадры ===
    output_folder = 'frames'
    os.makedirs(output_folder, exist_ok=True)
    video_id = str(random.randint(1, 1000000))

    # считаем FPS
    video_clip = VideoFileClip(video_path)
    original_fps = video_clip.fps
    print(original_fps)

    # Извлекаем аудио
    extracted_audio_path = video_id + ".mp3"
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
    video_clip = video_clip.set_audio(AudioFileClip(extracted_audio_path))
    video_clip.write_videofile(video_name_with_sound, codec='libx264')

    end_time = datetime.datetime.now()
    current_time = end_time.time()
    print("Конец:", current_time)

    # подсчёт времени
    spent_time = end_time - start_time
    print("Прошло времени:", spent_time)

    # удаление временных файлов
    os.remove(video_path)
    os.remove(output_video_path)
    os.remove(extracted_audio_path)
    shutil.rmtree(output_folder)

except Exception as e:
    print(f"Произошла ошибка: {e}")