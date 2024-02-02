import os
import numpy as np
from diffusers import KandinskyV22PriorEmb2EmbPipeline, KandinskyV22ControlnetImg2ImgPipeline
from diffusers.utils import load_image
from transformers import pipeline


class Image_Generator:
    def __init__(self, cuda_index):
        cuda_number = str(cuda_index)
        os.environ["CUDA_VISIBLE_DEVICES"] = cuda_number
        import torch
        self.torch = torch
        self.cuda_index = cuda_index
        self.pipe_prior = None
        self.pipe = None
        self.load_models()
        self.loaded = False

    def load_models(self):
        try:
            print(f"image model loading... GPU:{self.cuda_index}")
            self.pipe_prior = KandinskyV22PriorEmb2EmbPipeline.from_pretrained(
                "kandinsky-community/kandinsky-2-2-prior", torch_dtype=self.torch.float16
            )

            self.pipe = KandinskyV22ControlnetImg2ImgPipeline.from_pretrained(
                "kandinsky-community/kandinsky-2-2-controlnet-depth", torch_dtype=self.torch.float16
            )

            print(f"==========Images Model Loaded{self.cuda_index}!==========")
            self.loaded = True
        except Exception as e:
            print(f"Error while loading models: {e}")

    async def generate_image(self, prompt, negative_prompt, x, y, steps, seed, strength, strength_prompt,
                             strength_negative_prompt, image_name):
        try:
            def make_hint(image, depth_estimator):
                image = depth_estimator(image)["depth"]
                image = np.array(image)
                image = image[:, :, None]
                image = np.concatenate([image, image, image], axis=2)
                detected_map = self.torch.from_numpy(image).float() / 255.0
                hint = detected_map.permute(2, 0, 1)
                return hint

            # create generator
            generator = self.torch.Generator(device="cuda").manual_seed(seed)

            # make hint
            img = load_image(image_name).resize((x, y))
            depth_estimator = pipeline("depth-estimation")
            hint = make_hint(img, depth_estimator).unsqueeze(0).half().to("cuda:0")

            # run prior pipeline
            img_emb = self.pipe_prior(prompt=prompt, image=img, strength=strength_prompt,
                                      generator=generator)
            negative_emb = self.pipe_prior(prompt=negative_prompt, image=img,
                                           strength=strength_negative_prompt,
                                           generator=generator)

            # run controlnet img2img pipeline
            images = self.pipe(
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
            return image_name
        except Exception as e:
            error_message = f"Произошла ошибка: {e}"
            return error_message
