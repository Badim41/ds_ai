import os
import shutil

path = "D:/Games/output/song_output/song_output"
sorted_folders = []
for i in range(21):
    if i == 0:
        continue
    sorted_folders.append(path + "/" + str(i))

i = 0
for folder in sorted_folders:
    print(folder)
    i+=1
    for file in os.listdir(folder):
        if "Instrumental" in file:
            shutil.copy(folder + "/" + file, path + "/" + "inst")
            os.rename(path + "/" + "inst/" + file, path + "/" + f"inst/{i}.wav")
        if "_rmvpe.wav" in file:
            shutil.copy(folder + "/" + file, path + "/" + "vocal")
            os.rename(path + "/" + "vocal/" + file, path + "/" + f"vocal/{i}.wav")
        if "Vocals_Backup" in file:
            shutil.copy(folder + "/" + file, path + "/" + "back")
            os.rename(path + "/" + "back/" + file, path + "/" + f"back/{i}.wav")