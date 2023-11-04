import os
import time
cuda_number = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = cuda_number
import torch
import numpy as np
from diffusers import KandinskyV22PriorEmb2EmbPipeline, KandinskyV22ControlnetImg2ImgPipeline
from diffusers.utils import load_image
from transformers import pipeline
import datetime

from set_get_config import set_get_config_all_not_async


def generate_picture0():
    def make_hint(image, depth_estimator):
        image = depth_estimator(image)["depth"]
        image = np.array(image)
        image = image[:, :, None]
        image = np.concatenate([image, image, image], axis=2)
        detected_map = torch.from_numpy(image).float() / 255.0
        hint = detected_map.permute(2, 0, 1)
        return hint

    print(f"image model loading... GPU:{cuda_number}")
    pipe_prior = KandinskyV22PriorEmb2EmbPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-prior", torch_dtype=torch.float16
    )

    pipe = KandinskyV22ControlnetImg2ImgPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-controlnet-depth", torch_dtype=torch.float16
    )

    print(f"==========Images Model Loaded{cuda_number}!==========")
    set_get_config_all_not_async(f'Image{cuda_number}', "model_loaded", True)
    # loop update image prompt
    while True:
        try:
            # print(f"check prompt{cuda_number}")
            prompt = set_get_config_all_not_async(f'Image{cuda_number}', "prompt")
            if prompt == "None":
                time.sleep(0.1)
                continue
            set_get_config_all_not_async(f'Image{cuda_number}', "prompt", "None")
            start_time = datetime.datetime.now()
            current_time = start_time.time()
            print("Начало:", current_time)

            negative_prompt = set_get_config_all_not_async(f'Image{cuda_number}', "negative_prompt")
            x = int(set_get_config_all_not_async(f'Image{cuda_number}', "x"))
            y = int(set_get_config_all_not_async(f'Image{cuda_number}', "y"))
            steps = int(set_get_config_all_not_async(f'Image{cuda_number}', "steps"))
            seed = int(set_get_config_all_not_async(f'Image{cuda_number}', "seed"))
            strength = float(set_get_config_all_not_async(f'Image{cuda_number}', "strength"))
            strength_prompt = float(set_get_config_all_not_async(f'Image{cuda_number}', "strength_prompt"))
            strength_negative_prompt = float(set_get_config_all_not_async(f'Image{cuda_number}', "strength_negative_prompt"))
            image_name = set_get_config_all_not_async(f'Image{cuda_number}', "input")
            # create pipes
            print(f"image_generate(1/5), GPU:{cuda_number}")
            pipe_prior = pipe_prior.to("cuda:0")
            pipe = pipe.to("cuda:0")
            print(f"image_generate(2/5), GPU:{cuda_number}")

            # create generator
            generator = torch.Generator(device="cuda").manual_seed(seed)
            print(f"image_generate(3/5), GPU:{cuda_number}")

            # make hint
            img = load_image(image_name).resize((x, y))
            depth_estimator = pipeline("depth-estimation")
            hint = make_hint(img, depth_estimator).unsqueeze(0).half().to("cuda:0")
            print(f"image_generate(4/5), GPU:{cuda_number}")

            # run prior pipeline
            img_emb = pipe_prior(prompt=prompt, image=img, strength=strength_prompt, generator=generator)
            negative_emb = pipe_prior(prompt=negative_prompt, image=img, strength=strength_negative_prompt,
                                      generator=generator)
            print(f"image_generate(5/5), GPU:{cuda_number}")
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
            set_get_config_all_not_async(f'Image{cuda_number}', "spent_time", spent_time)
            set_get_config_all_not_async(f'Image{cuda_number}', "result", image_name)
        except Exception as e:
            print(f"Произошла ошибка: {e}")