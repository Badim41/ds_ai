import argparse

import cv2
from kandinsky2 import get_kandinsky2

def generate_picture(prompt, negative_prompt, x, y, steps, seed):

    model = get_kandinsky2('cuda', task_type='text2img', cache_dir='/tmp/kandinsky2', model_version='2.1',
                           use_flash_attention=False)
    images = model.generate_text2img(prompt, num_steps=steps, batch_size=1, guidance_scale=4, h=y, w=x,
                                     sampler='p_sampler', prior_cf_scale=4, prior_steps="5", )
    cv2.imwrite("picture.png", images.images[0])
    print("Изображение сохранено как picture.png")


if __name__ == '__main__':
    print("image0")
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
