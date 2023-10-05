lines = ["абаабаб", "ааава"]
with open("caversAI/audio_links.txt", "a") as writer:
    for line in lines:
        writer.write(line + "\n")