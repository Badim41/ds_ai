from nomic.gpt4all import GPT4AllGPU
from discord_bot import config
import textwrap
import time
model_loaded = False
def run():
    while True:
        model = GPT4AllGPU("decapoda-research/llama-7b-hf")
        model_loaded = True
        with open("nomic/gpt_prompt.txt", "r", encoding="utf-8") as reader:
            lines = reader.readlines()
            if lines[0] == "enter prompt":
                time.sleep(0.25)
                continue
            else:
                with open("nomic/gpt_prompt.txt", "w", encoding="utf-8") as writer:
                    writer.write("enter prompt")
                prompt = ''.join(lines)
                config.read('config.ini')
                tokens = config.getint('Default', 'prompt_length')
                config_gpt = {'num_beams': 2,
                              'min_new_tokens': tokens,
                              'max_length': tokens * 12,
                              'repetition_penalty': 2.0}
                out = model.generate(prompt, config_gpt)
                with open("nomic/gpt_result.txt", "w", encoding="utf-8") as writer:
                    writer.writelines(out)
                print("DEV_TEMP_OUTPUT:", out)