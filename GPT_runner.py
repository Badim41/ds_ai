import configparser
import multiprocessing
import subprocess

from transformers import AutoTokenizer
from auto_gptq import AutoGPTQForCausalLM
import time


config = configparser.ConfigParser()

async def set_get_config(key, value=None):
    config.read('config.ini')
    if value is None:
        return config.get('gpt', key)

    config.set('gpt', key, str(value))
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def run_pictures(command):
    print("subprocess")
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    print(f"Выполнено: {command}\nВыход: {out.decode('utf-8')}\nОшибка: {err.decode('utf-8')}")


def run():
    model_name = 'fffrrt/ruGPT-3.5-13B-GPTQ'
    model_basename = 'gptq_model-4bit-128g'
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=False)
    model = AutoGPTQForCausalLM.from_quantized(model_name,
                                               model_basename=model_basename,
                                               use_safetensors=True,
                                               trust_remote_code=True,
                                               device="cuda:0",
                                               use_triton=False,
                                               quantize_config=None)
    set_get_config("gpt", value=True)
    print("==========GPT Model Loaded!==========")
    # load image model
    command = (
    "python",
    "image_create.py"
    ) 
    print("subprocess0")
    pool = multiprocessing.Pool(processes=2)
    pool.apply_async(run_pictures(command,))
    pool.close()
    print("subprocess1")
    while True:
        prompt = set_get_config("gpt_prompt")
        if prompt == "None":
            time.sleep(0.25)
            continue
        else:
            print("found_prompt")
            set_get_config("gpt_prompt", value="None")
            prompt = prompt.replace("\\n", "\n")
            tokens = config.getint('gpt', 'prompt_length')
            encoded_input = tokenizer(prompt, return_tensors='pt').to('cuda:0')
            output = model.generate(
                **encoded_input,
                num_beams=4,
                max_new_tokens=tokens,
                no_repeat_ngram_size=2
                # num_return_sequences=5,
                # do_sample=True
            )
            out = tokenizer.decode(output[0], skip_special_tokens=True)
            print("generated_prompt")
            if '\n\n' in out:
                print("\\n\\n in sentence")
                index = out.find('\n\n')
                if len(out) - index > 50:
                    remove_tokens = str(index / len(out) * tokens)
                    print(f"слишком много токенов, советуем убрать {remove_tokens[remove_tokens.find('.'):]} токенов")
                out = out[:index]
                print("\\n\\n deleted")
            else:
                print("\\n\\n не найден")
            set_get_config("gpt_result", out + "$$")
            print("DEV_TEMP_OUTPUT:", out)
