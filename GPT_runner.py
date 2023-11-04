from transformers import AutoTokenizer
from auto_gptq import AutoGPTQForCausalLM
import time

from set_get_config import set_get_config_all_not_async


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
    set_get_config_all_not_async("gpt", "gpt", "True")
    print("==========GPT Model Loaded!==========")

    # loop update gpt prompt
    while True:
        prompt = set_get_config_all_not_async("gpt", "gpt_prompt")
        if prompt == "None":
            time.sleep(0.25)
            continue
        else:
            print("found_prompt")
            set_get_config_all_not_async("gpt", "gpt_prompt")
            # prompt = prompt.replace("\\n", "\n")
            tokens = int(set_get_config_all_not_async('gpt', 'prompt_length'))
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
            print("generated. DEV_TEMP_OUTPUT:", out)
            if '\n\n' in out:
                print("\\n\\n in sentence")
                index = out.find('\n\n')
                out = out[:index]
                if index - len(out) > 50:
                    remove_tokens = str(index / len(out) * tokens)
                    remove_tokens = remove_tokens[:remove_tokens.find('.')]
                    out += f"\n||слишком много токенов, советуем убрать {remove_tokens} токенов||"
                print("\\n\\n deleted")
            else:
                print("\\n\\n не найден")
            set_get_config_all_not_async("gpt", "gpt_result", out + "$$")
