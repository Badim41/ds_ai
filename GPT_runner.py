from transformers import AutoTokenizer
from auto_gptq import AutoGPTQForCausalLM
from discord_bot import config
import time
model_loaded = False
def run():
    global model_loaded
    model_name = 'fffrrt/ruGPT-3.5-13B-GPTQ'
    model_basename = 'gptq_model-4bit-128g'
    print("loading model")
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoGPTQForCausalLM.from_quantized(model_name,
                                               model_basename=model_basename,
                                               use_safetensors=True,
                                               trust_remote_code=True,
                                               device="cuda:0",
                                               use_triton=False,
                                               quantize_config=None)
    model_loaded = True
    while True:
        with open("gpt_prompt.txt", "r", encoding="utf-8") as reader:
            lines = reader.readlines()
            if lines[0] == "enter prompt":
                time.sleep(0.25)
                continue
            else:
                with open("gpt_prompt.txt", "w", encoding="utf-8") as writer:
                    writer.write("enter prompt")
                prompt = ''.join(lines)
                config.read('config.ini')
                tokens = config.getint('Default', 'prompt_length')
                encoded_input = tokenizer(prompt, return_tensors='pt').to('cuda:0')
                output = model.generate(
                    **encoded_input,
                    num_beams=4,
                    max_new_tokens=tokens,
                    no_repeat_ngram_size=2,
                    # num_return_sequences=5,
                    # do_sample=True
                )

                out = tokenizer.decode(output[0], skip_special_tokens=True)
                # config_gpt = {'num_beams': 2,
                #               'min_new_tokens': tokens,
                #               'max_length': tokens * 12,
                #               'repetition_penalty': 2.0}
                # out = model.generate(prompt, config_gpt)
                with open("gpt_result.txt", "w", encoding="utf-8") as writer:
                    writer.writelines(out)
                print("DEV_TEMP_OUTPUT:", out)