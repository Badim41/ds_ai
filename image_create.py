import argparse
import random
import torch
import numpy as np
from diffusers import KandinskyV22PriorEmb2EmbPipeline, KandinskyV22ControlnetImg2ImgPipeline
from diffusers.utils import load_image
from transformers import pipeline
import datetime


negative_prompt = ("lowres, "
                   "text, "
                   "error, "
                   "cropped, "
                   "worst quality, "
                   "low quality, "
                   "mutilated, "
                   "out of frame, "
                   "extra fingers, "
                   "poorly drawn hands, "
                   "mutation, "
                   "deformed, "
                   "blurry, "
                   "bad proportions, "
                   "extra limbs, "
                   "cloned face, "
                   "disfigured, "
                   "gross proportions, "
                   "malformed limbs, "
                   "missing arms, "
                   "missing legs, "
                   "extra arms, "
                   "extra legs, "
                   "fused fingers, "
                   "too many fingers, "
                   "long neck, "
                   "username, "
                   "watermark, "
                   "signature")
prompt = 'HD image'


def generate_picture(prompt=prompt, negative_prompt=negative_prompt, x=512, y=512, steps=50,
                     seed=random.randint(1, 10000), strenght=0.5):
    # test IMAGES 1
    current_datetime = datetime.datetime.now()
    current_time = current_datetime.time()
    print("Начало:", current_time)

    img = load_image(
        "https://huggingface.co/datasets/hf-internal-testing/diffusers-images/resolve/main" "/kandinskyv22/cat.png"
    ).resize((x, y))

    def make_hint(image, depth_estimator):
        image = depth_estimator(image)["depth"]
        image = np.array(image)
        image = image[:, :, None]
        image = np.concatenate([image, image, image], axis=2)
        detected_map = torch.from_numpy(image).float() / 255.0
        hint = detected_map.permute(2, 0, 1)
        return hint

    depth_estimator = pipeline("depth-estimation")
    hint = make_hint(img, depth_estimator).unsqueeze(0).half().to("cuda")

    pipe_prior = KandinskyV22PriorEmb2EmbPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-prior", torch_dtype=torch.float16
    )
    pipe_prior = pipe_prior.to("cuda")

    pipe = KandinskyV22ControlnetImg2ImgPipeline.from_pretrained(
        "kandinsky-community/kandinsky-2-2-controlnet-depth", torch_dtype=torch.float16
    )
    pipe = pipe.to("cuda")

    generator = torch.Generator(device="cuda").manual_seed(seed)

    # run prior pipeline

    img_emb = pipe_prior(prompt=prompt, image=img, strength=0.85, generator=generator)
    negative_emb = pipe_prior(prompt=negative_prompt, image=img, strength=1, generator=generator)
    # run controlnet img2img pipeline
    images = pipe(
        image=img,
        strength=strenght,
        image_embeds=img_emb.image_embeds,
        negative_image_embeds=img_emb.image_embeds,
        hint=hint,
        num_inference_steps=steps,
        generator=generator,
        height=y,
        width=x,
    ).images

    images[0].save(f"image{random.randint(1, 10000)}.png")

    current_datetime = datetime.datetime.now()
    current_time = current_datetime.time()
    print("Конец:", current_time)


if __name__ == '__main__':
    print("image0")
    parser = argparse.ArgumentParser(description='Generate a AI cover song in the song_output/id directory.',
                                     add_help=True)
    parser.add_argument('-prompt', '--prompt', type=str, default=prompt,
                        help='prompt for picture')
    parser.add_argument('-nprompt', '--negative-prompt', type=str, default=negative_prompt,
                        help='negative prompt for picture')
    parser.add_argument('-x', '--x', type=int, default='512',
                        help='size X')
    parser.add_argument('-y', '--y', type=int, default='512',
                        help='size Y')
    parser.add_argument('-steps', '--steps', type=int, default='25',
                        help='steps')
    parser.add_argument('-seed', '--seed', type=int, default=random.randint(1, 10000),
                        help='seed')
    parser.add_argument('-strenght', '--strenght', type=float, default=0.5,
                        help='strenght of changing')
    args = parser.parse_args()
    generate_picture(prompt=args.prompt, negative_prompt=args.negative_prompt, x=args.x, y=args.y, steps=args.steps,
                     seed=args.seed, strenght=args.strenght)
