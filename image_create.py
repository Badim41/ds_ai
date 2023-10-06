# !git clone https://github.com/ai-forever/diffusers.git
import argparse
import random
from diffusers import KandinskyV22Pipeline, KandinskyV22PriorPipeline
import torch
from transformers import CLIPVisionModelWithProjection
from diffusers.models import UNet2DConditionModel
import cv2

def generate_picture(prompt, negative_prompt, x, y, steps, seed):
    image_encoder = CLIPVisionModelWithProjection.from_pretrained(
        'kandinsky-community/kandinsky-2-2-prior',
        subfolder='image_encoder'
    ).half().to("cuda:0")
    print("image3")
    unet = UNet2DConditionModel.from_pretrained(
        'kandinsky-community/kandinsky-2-2-decoder',
        subfolder='unet'
    ).half().to("cuda:0")
    print("image4")
    prior = KandinskyV22PriorPipeline.from_pretrained(
        'kandinsky-community/kandinsky-2-2-prior',
        image_encoder=image_encoder,
        torch_dtype=torch.float16
    ).to("cuda:0")
    print("image5")
    decoder = KandinskyV22Pipeline.from_pretrained(
        'kandinsky-community/kandinsky-2-2-decoder',
        unet=unet,
        torch_dtype=torch.float16
    ).to("cuda:0")
    print("image6")
    torch.manual_seed(seed)

    negative_prior_prompt = negative_prompt
    img_emb = prior(
        prompt=prompt,
        num_inference_steps=steps,
        num_images_per_prompt=1
    )
    print("image7")

    negative_emb = prior(
        prompt=negative_prior_prompt,
        num_inference_steps=steps,
        num_images_per_prompt=1
    )
    print("image8")

    images = decoder(
        image_embeds=img_emb.image_embeds,
        negative_image_embeds=negative_emb.image_embeds,
        num_inference_steps=75,
        height=y,
        width=x)
    print("image9")
    cv2.imwrite("picture.png", images.images[0])
    print("Изображение сохранено как picture.png")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a AI cover song in the song_output/id directory.',
                                     add_help=True)
    parser.add_argument('-prompt', '--prompt', type=str, default='HD image',
                        help='prompt for picture')
    parser.add_argument('-nprompt', '--negative-prompt', type=str, default='NSFW',
                        help='negative prompt for picture')
    parser.add_argument('-x', '--x', type=int, default='512',
                        help='size X')
    parser.add_argument('-y', '--y', type=int, default='512',
                        help='size Y')
    parser.add_argument('-steps', '--steps', type=int, default='25',
                        help='steps')
    parser.add_argument('-seed', '--seed', type=int, default=random.randint(1, 10000),
                       help='seed')
    print("image1")
    args = parser.parse_args()
    print("image2")
    generate_picture(args.prompt, args.negative_prompt, args.x, args.y, args.steps, args.seed)
