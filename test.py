import os
import random
import shutil

import cv2
from moviepy.editor import VideoFileClip, AudioFileClip
from moviepy.audio.fx import audio_fadein, audio_fadeout
import imageio
import os

video_path = "C:/Users/as280/Downloads/videoplayback.mp4"
output_folder = 'frames'
os.makedirs(output_folder, exist_ok=True)
video_id = str(random.randint(1, 1000000))

# считаем FPS
cap = cv2.VideoCapture(video_path)
original_fps = cap.get(cv2.CAP_PROP_FPS)
print(original_fps)

# Извлекаем аудио
extracted_audio_path = video_id + ".mp3"
video_clip = VideoFileClip(video_path)
audio_clip = video_clip.audio
audio_clip.write_audiofile(extracted_audio_path)

# Размер и пропуск изображений
# 480p=640×480
# 360p=480×360
# 240p=426×240
# 144p=256×144
video_
if
fps_output = 5 # frame/sec (1, 2, 3, 5, 10, 15, 30)
save_img_step = original_fps / fps_output


frame_number = 0

while True:
    frame_number += 1
    ret, frame = cap.read()
    if not frame_number % save_img_step == 0:
        continue
    if not ret:
        break
    frame = cv2.resize(frame, (new_width, new_height))
    frame_filename = os.path.join(output_folder, f'{frame_number:09d}.png')
    cv2.imwrite(frame_filename, frame)


cap.release()

# === Снова создаём видео ===



# Папка с изображениями
image_folder = 'frames'

# Список изображений
images = []
for filename in sorted(os.listdir(image_folder)):
    if filename.endswith('.png'):
        image_path = os.path.join(image_folder, filename)
        images.append(imageio.imread(image_path))
output_video_path = video_id + '.mp4'

# Создание видео
print(int(original_fps / save_img_step))
imageio.mimsave(output_video_path, images, fps=int(original_fps / save_img_step))

# добавляем звук
video_clip = VideoFileClip(output_video_path)
video_clip = video_clip.set_audio(AudioFileClip(extracted_audio_path))
video_clip.write_videofile(video_id + "_with_sound" + ".mp4", codec='libx264')

# удаление временных файлов
# os.remove(video_path)
os.remove(output_video_path)
os.remove(extracted_audio_path)
shutil.rmtree(output_folder)