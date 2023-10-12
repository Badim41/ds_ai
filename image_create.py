import argparse
import random
import time

import torch
import numpy as np
from diffusers import KandinskyV22PriorEmb2EmbPipeline, KandinskyV22ControlnetImg2ImgPipeline
from diffusers.utils import load_image
from transformers import pipeline
import datetime
import configparser

config = configparser.ConfigParser()


def set_get_config(key, value=None):
    config.read('config.ini')
    if value is None:
        return config.get('gpt', key)

    config.set('Image', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def generate_picture():
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
    pipe_prior = pipe_prior.to("cuda")
    print("image3")
    pipe = KandinskyV22ControlnetImg2ImgPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-controlnet-depth", torch_dtype=torch.float16
    )
    pipe = pipe.to("cuda")
    print("==========Images Model Loaded!==========")
    set_get_config("model_loaded", True)
    # loop update image prompt
    while True:
        prompt = set_get_config("gpt_prompt")
        if prompt == "None":
            time.sleep(0.25)
            continue
        set_get_config("gpt_prompt", "None")
        current_datetime = datetime.datetime.now()
        current_time = current_datetime.time()
        print("Начало:", current_time)

        negative_prompt = set_get_config("negative_prompt")
        x = int(set_get_config("x"))
        y = int(set_get_config("y"))
        steps = int(set_get_config("steps"))
        seed = int(set_get_config("seed"))
        strength = float(set_get_config("strength"))
        strength_prompt = float(set_get_config("strength_prompt"))
        strength_negative_prompt = float(set_get_config("strength_negative_prompt"))

        # create generator
        generator = torch.Generator(device="cuda").manual_seed(seed)

        # make hint
        img = load_image(set_get_config("input")).resize((x, y))
        depth_estimator = pipeline("depth-estimation")
        hint = make_hint(img, depth_estimator).unsqueeze(0).half().to("cuda")

        # run prior pipeline
        img_emb = pipe_prior(prompt=prompt, image=img, strength=strength_prompt, generator=generator)
        negative_emb = pipe_prior(prompt=negative_prompt, image=img, strength=strength_negative_prompt,
                                  generator=generator)

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
        images_filename = "image" + str(random.randint(1, 1000000)) + ".png"
        images[0].save(images_filename)

        current_datetime = datetime.datetime.now()
        current_time = current_datetime.time()
        print("Конец:", current_time)
        set_get_config("result", images_filename)


# if __name__ == '__main__':
print("image0")
generate_picture()
# generate_picture(prompt=args.prompt, negative_prompt=args.negative_prompt, x=args.x, y=args.y, steps=args.steps,
# seed=args.seed, strenght=args.strenght)
