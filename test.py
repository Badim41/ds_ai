from gpt4all import GPT4All
model = GPT4All("nous-hermes-13b.ggmlv3.q4_0.bin")
output = model.generate("The capital of France is ", max_tokens=3)
print(output)