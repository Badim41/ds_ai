keys = "1;2;3;4;5".split(";")

while not keys == "None":
    if len(keys) > 1 and isinstance(keys, list):
        keys = keys[1:]
    else:
        keys = "None"
    print(keys)
