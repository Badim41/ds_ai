import asyncio
import imageio
import os
import random
import shutil
import subprocess
import time
from moviepy.editor import VideoFileClip, AudioFileClip

from PIL import Image

from cover_gen import run_ai_cover_gen
from function import Character
from discord_tools.logs import Logs, Color
logger = Logs(warnings=True)


async def image_change(output_folder, prompt, negative_prompt, x, y, steps, seed, strength, strength_prompt,
                       strength_negative_prompt, cuda_all: int, cuda_index: int, image_generator):
    print("image changing...", cuda_index)
    # several GPU
    for i, filename in enumerate(sorted(os.listdir(output_folder))):
        if i % cuda_all == cuda_index:
            continue
        if filename.endswith('.png'):
            await image_generator.generate_image(prompt, negative_prompt, x, y, steps, seed, strength, strength_prompt,
                                                  strength_negative_prompt, filename)
    return


async def video_pipeline(video_path, fps_output, video_extension, prompt, voice_name, video_id, cuda_all, image_generators, strength_negative_prompt, strength_prompt,
                         strength, seed, steps, negative_prompt):
    try:

        # === разбиваем видео на карды ===
        output_folder = 'frames'
        os.makedirs(output_folder, exist_ok=True)

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
        # 720p=1280×720
        # 480p=854×480
        # 360p=640×360
        # 240p=426×240
        # 144p=256×144
        new_width = None
        new_height = None
        old_width = None
        old_height = None

        if video_extension == "720p":
            old_width = 1280
            old_height = 720
            new_width = 1280
            new_height = 704
        elif video_extension == "480p":
            old_width = 854
            old_height = 480
            new_width = 832
            new_height = 480
        elif video_extension == "360p":
            old_width = 640
            old_height = 360
            new_width = 640
            new_height = 352
        elif video_extension == "240p":
            old_width = 426
            old_height = 240
            new_width = 448
            new_height = 240
        elif video_extension == "144p":
            old_width = 256
            old_height = 144
            new_width = 256
            new_height = 128

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
        functions = [image_change(output_folder=output_folder, prompt=prompt, negative_prompt=negative_prompt, x=x, y=y,
                                  steps=steps, seed=seed, strength=strength, strength_prompt=strength_prompt,
                                  strength_negative_prompt=strength_negative_prompt, cuda_all=cuda_all, image_generator=image_generator)
                     for image_generator in image_generators]
        await asyncio.gather(*functions)  # результаты всех функций

        character = Character(voice_name)
        pitch = character.pitch
        audio_path = await run_ai_cover_gen(song_input=extracted_audio_path, rvc_dirname=voice_name, pitch=pitch, cuda_number=cuda_all[0])

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

        # удаление временных файлов
        os.remove(video_path)
        os.remove(output_video_path)
        os.remove(extracted_audio_path)
        shutil.rmtree(output_folder)
        return video_name_with_sound
    except Exception as e:
        print(f"Произошла ошибка: {e}")

    return None
