import os
import cv2

video_path = "C:/Users/as280/Downloads/videoplayback.mp4"
output_folder = 'frames'
os.makedirs(output_folder, exist_ok=True)

cap = cv2.VideoCapture(video_path)
original_fps = cap.get(cv2.CAP_PROP_FPS)
print(original_fps)

# Размер и пропуск изображений
new_width = 640
new_height = 480

save_img_step = original_fps / 30 # frame/sec (1, 2, 3, 5, 10, 15, 30)


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

# Снова создаём видео

import imageio
import os

# Папка с изображениями
image_folder = 'frames'

# Список изображений
images = []
for filename in sorted(os.listdir(image_folder)):
    if filename.endswith('.png'):
        image_path = os.path.join(image_folder, filename)
        images.append(imageio.imread(image_path))
output_video_path = 'output_video.mp4'

# Создание видео
print(int(original_fps / save_img_step))
imageio.mimsave(output_video_path, images, fps=int(original_fps / save_img_step))