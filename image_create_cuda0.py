import os
import struct
import time
import configparser

os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
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
        return config.get(f'Image', key)

    config.set(f'Image', key, str(value))
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


def make_hint(image, depth_estimator):
    image = depth_estimator(image)["depth"]
    image = np.array(image)
    image = image[:, :, None]
    image = np.concatenate([image, image, image], axis=2)
    detected_map = torch.from_numpy(image).float() / 255.0
    hint = detected_map.permute(2, 0, 1)
    print("image-Hint")
    return hint


def generate_picture():
    print("image model loading... GPU:0")
    pipe_prior_0 = KandinskyV22PriorEmb2EmbPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-prior", torch_dtype=torch.float16
    )

    pipe_0 = KandinskyV22ControlnetImg2ImgPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-controlnet-depth", torch_dtype=torch.float16
    )

    print("image model loading... GPU:1")
    pipe_prior_1 = KandinskyV22PriorEmb2EmbPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-prior", torch_dtype=torch.float16
    )

    pipe_1 = KandinskyV22ControlnetImg2ImgPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-controlnet-depth", torch_dtype=torch.float16
    )

    # Wrap the pipelines with DataParallel
    pipe_prior_0 = torch.nn.DataParallel(pipe_prior_0)
    pipe_0 = torch.nn.DataParallel(pipe_0)
    pipe_prior_1 = torch.nn.DataParallel(pipe_prior_1)
    pipe_1 = torch.nn.DataParallel(pipe_1)

    print(f"==========Images Model Loaded!==========")
    set_get_config("model_loaded", True)
    # loop update image prompt
    while True:
        try:
            # print(f"check prompt{cuda_number}")
            prompt = set_get_config("prompt")
            if prompt == "None":
                time.sleep(0.1)
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
            print(f"image_generate(1/5), GPU:0")
            pipe_prior_0 = pipe_prior_0.to("cuda:0")
            pipe_0 = pipe_0.to("cuda:0")
            print(f"image_generate(2/5), GPU:0")

            print(f"image_generate(1/5), GPU:1")
            pipe_prior_1 = pipe_prior_1.to("cuda:1")
            pipe_1 = pipe_1.to("cuda:1")
            print(f"image_generate(2/5), GPU:1")

            # create generator
            generator_0 = torch.Generator(device="cuda:0").manual_seed(seed)
            generator_1 = torch.Generator(device="cuda:1").manual_seed(seed)
            print(f"image_generate(3/5), GPU:0")

            # make hint
            img = load_image(image_name).resize((x, y))
            depth_estimator = pipeline("depth-estimation")
            hint = make_hint(img, depth_estimator).unsqueeze(0).half().to("cuda")
            print(f"image_generate(4/5), GPU:0")

            # run prior pipeline
            img_emb_0 = pipe_prior_0(prompt=prompt, image=img, strength=strength_prompt, generator=generator_0)
            img_emb_1 = pipe_prior_1(prompt=prompt, image=img, strength=strength_prompt, generator=generator_1)
            negative_emb_0 = pipe_prior_0(prompt=negative_prompt, image=img, strength=strength_negative_prompt,
                                          generator=generator_0)
            negative_emb_1 = pipe_prior_1(prompt=negative_prompt, image=img, strength=strength_negative_prompt,
                                          generator=generator_1)
            print(f"image_generate(5/5), GPU:0")
            # run controlnet img2img pipeline
            images_0 = pipe_0(
                image=img,
                strength=strength,
                image_embeds=img_emb_0.image_embeds,
                negative_image_embeds=negative_emb_0.image_embeds,
                hint=hint,
                num_inference_steps=steps,
                generator=generator_0,
                height=y,
                width=x,
            ).images

            images_1 = pipe_1(
                image=img,
                strength=strength,
                image_embeds=img_emb_1.image_embeds,
                negative_image_embeds=negative_emb_1.image_embeds,
                hint=hint,
                num_inference_steps=steps,
                generator=generator_1,
                height=y,
                width=x,
            ).images

            images_0[0].save(image_name)
            images_1[0].save(image_name)

            end_time = datetime.datetime.now()
            current_time = end_time.time()
            print("Конец:", current_time)

            spent_time = end_time - start_time
            print("Прошло времени:", spent_time)
            set_get_config("spent_time", spent_time)
            set_get_config("result", image_name)
        except Exception as e:
            print(f"Произошла ошибка: {e}")
