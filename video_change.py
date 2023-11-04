import asyncio
import multiprocessing
import random
import shutil
import subprocess
import time
from PIL import Image
from moviepy.editor import VideoFileClip, AudioFileClip
import imageio
import os
from set_get_config import set_get_config_all

#                                       количество---индекс
async def image_change(output_folder, prompt, cuda_number, cuda_index):
    print("image changing...")
    if cuda_number == 1:
        # 1 GPU
        for filename in sorted(os.listdir(output_folder)):
            if filename.endswith('.png'):
                print("changing...", filename)
                await set_get_config_all(f"Image", "result", "None")
                await set_get_config_all(f"Image", "input", "frames/" + filename)
                await set_get_config_all(f"Image", "prompt", prompt)
                # wait for answer
                while True:
                    if not await set_get_config_all(f"Image", "result", None) == "None":
                        break
                    await asyncio.sleep(0.25)
        await set_get_config_all(f"Video", f"result_video{cuda_index}", True)
    else:
        # 2 GPU
        i = 0
        for filename in sorted(os.listdir(output_folder)):
            # чётные карды на 2-ой видеокарте, нечётные - на 1-ой
            i += 1
            if i % 2 == cuda_index:
                continue
            if filename.endswith('.png'):
                print("changing...", filename)
                await set_get_config_all(f"Image{cuda_index}", "result", "None")
                await set_get_config_all(f"Image{cuda_index}", "input", "frames/" + filename)
                await set_get_config_all(f"Image{cuda_index}", "prompt", prompt)
                # wait for answer
                while True:
                    if not await set_get_config_all(f"Image{cuda_index}", "result", None) == "None":
                        break
                    await asyncio.sleep(0.25)
        await set_get_config_all(f"Video", f"result_video{cuda_index}", True)
    return


async def video_pipeline(video_path, fps_output, video_extension, prompt, voice,
                         pitch, indexrate, loudness, main_vocal, back_vocal,
                         music, roomsize, wetness, dryness, cuda_numbers):
    try:

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
        if len(cuda_numbers) == 1:
            await set_get_config_all(f"Video", f"result_video0", False)
            pool = multiprocessing.Pool(processes=1)
            pool.apply_async(image_change(output_folder, prompt, 1, 0))
            pool.close()
        else:
            await set_get_config_all(f"Video", f"result_video0", False)
            await set_get_config_all(f"Video", f"result_video1", False)
            await asyncio.gather(image_change(output_folder, prompt, len(cuda_numbers), 0), image_change(output_folder, prompt, len(cuda_numbers), 1))  # результаты всех функций

        # wait for results
        for i in cuda_numbers:
            while True:
                if await set_get_config_all(f"Video", f"result_video{i}", None) == "True":
                    break
                await asyncio.sleep(5)

        # === обработка звука ===
        if not voice == "None":
            await set_get_config_all("voice", "generated", "None")
            command = [
                "python",
                "main_cuda0.py",
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

        # удаление временных файлов
        os.remove(video_path)
        os.remove(output_video_path)
        os.remove(extracted_audio_path)
        shutil.rmtree(output_folder)
        return video_name_with_sound
    except Exception as e:
        print(f"Произошла ошибка: {e}")

    return None
