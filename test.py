from PIL import Image
import numpy as np

# Создаем массив с шумом
width, height = 500, 500
noise = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

# Создаем объект Image из массива шума
image = Image.fromarray(noise)

# Сохраняем изображение
image.save("1.png")
