import os
import struct
import time
import configparser
cuda_number = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = cuda_number
import torch
import numpy as np
from diffusers import KandinskyV22PriorEmb2EmbPipeline, KandinskyV22ControlnetImg2ImgPipeline
from diffusers.utils import load_image
from transformers import pipeline
import datetime

config = configparser.ConfigParser()

def set_get_config(key, value=None):
    config.read('config.ini')
    if value is None:
        return config.get(f'Image{cuda_number}', key)

    config.set(f'Image{cuda_number}', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


async def get_image_dimensions(file_path):
    with open(file_path, 'rb') as file:
        data = file.read(24)

    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return struct.unpack('>ii', data[16:24])
    elif data[:6] in (b'GIF87a', b'GIF89a') and data[10:12] == b'\x00\x00':
        return struct.unpack('<HH', data[6:10])
    elif data.startswith(b'\xff\xd8\xff\xe0') and data[6:10] == b'JFIF':
        return struct.unpack('>H', data[7:9])[0], struct.unpack('>H', data[9:11])[0]
    elif data.startswith(b'\xff\xd8\xff\xe1') and data[6:10] == b'Exif':
        return struct.unpack('<HH', data[10:14])[0], struct.unpack('<HH', data[14:18])[0]
    else:
        raise ValueError("Формат не поддерживается")


def generate_picture0():
    # test IMAGES 1
    print("image1")

    def make_hint(image, depth_estimator):
        image = depth_estimator(image)["depth"]
        image = np.array(image)
        image = image[:, :, None]
        image = np.concatenate([image, image, image], axis=2)
        detected_map = torch.from_numpy(image).float() / 255.0
        hint = detected_map.permute(2, 0, 1)
        print("image-Hint")
        return hint

    print("image2")
    pipe_prior = KandinskyV22PriorEmb2EmbPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-prior", torch_dtype=torch.float16
    )

    print("image3")
    pipe = KandinskyV22ControlnetImg2ImgPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-controlnet-depth", torch_dtype=torch.float16
    )

    print("==========Images Model Loaded0!==========")
    set_get_config("model_loaded", True)
    # loop update image prompt
    while True:
        try:
            print(f"check prompt{cuda_number}")
            prompt = set_get_config("prompt")
            if prompt == "None":
                time.sleep(1)
                continue
            set_get_config("prompt", "None")
            start_time = datetime.datetime.now()
            current_time = start_time.time()
            print("Начало:", current_time)

            negative_prompt = set_get_config("negative_prompt")
            x = int(set_get_config("x"))
            y = int(set_get_config("y"))
            steps = int(set_get_config("steps"))
            seed = int(set_get_config("seed"))
            strength = float(set_get_config("strength"))
            strength_prompt = float(set_get_config("strength_prompt"))
            strength_negative_prompt = float(set_get_config("strength_negative_prompt"))
            image_name = set_get_config("input")
            # create pipes
            print("image_generate1")
            pipe_prior = pipe_prior.to("cuda")
            pipe = pipe.to("cuda")
            print("image_generate2")

            # create generator
            generator = torch.Generator(device="cuda").manual_seed(seed)
            print("image_generate3")

            # make hint
            img = load_image(image_name).resize((x, y))
            depth_estimator = pipeline("depth-estimation")
            hint = make_hint(img, depth_estimator).unsqueeze(0).half().to("cuda")
            print("image_generate4")

            # run prior pipeline
            img_emb = pipe_prior(prompt=prompt, image=img, strength=strength_prompt, generator=generator)
            negative_emb = pipe_prior(prompt=negative_prompt, image=img, strength=strength_negative_prompt,
                                      generator=generator)
            print("image_generate5")
            # run controlnet img2img pipeline
            images = pipe(
                image=img,
                strength=strength,
                image_embeds=img_emb.image_embeds,
                negative_image_embeds=negative_emb.image_embeds,
                hint=hint,
                num_inference_steps=steps,
                generator=generator,
                height=y,
                width=x,
            ).images

            images[0].save(image_name)

            end_time = datetime.datetime.now()
            current_time = end_time.time()
            print("Конец:", current_time)

            spent_time = end_time - start_time
            print("Прошло времени:", spent_time)
            set_get_config("spent_time", spent_time)
            set_get_config("result", image_name)
        except Exception as e:
            print(f"Произошла ошибка: {e}")
