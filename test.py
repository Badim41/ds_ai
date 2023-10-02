from pathlib import Path
from gpt4all import GPT4All

model_name = 'orca-mini-3b.ggmlv3.q4_0.bin'
model_path = Path.home() / '.local' / 'share' / 'nomic.ai' / 'GPT4All'
model = GPT4All(model_name, model_path)