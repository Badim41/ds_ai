lines = ["123", "321"]

with open("caversAI/audio_links.txt", "a") as writer:
    for line in lines:
        writer.write(line + "\n")