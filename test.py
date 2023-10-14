import os


def list_python_files(root_dir):
    lines_number = 0
    for foldername, subfolders, filenames in os.walk(root_dir):
        if 'venv' in subfolders:
            print("venv")
            subfolders.remove('venv')
        if 'discord' in subfolders:
            print("discord")
            subfolders.remove('discord')
        # if 'infer_pack' in subfolders:
        #     print("infer_pack")
        #     subfolders.remove('infer_pack')
        if 'src' in subfolders:
            print("src")
            subfolders.remove('src')

        for filename in filenames:
            if filename.endswith(".py"):
                print(os.path.join(foldername, filename))
                with open(os.path.join(foldername, filename), "r", encoding="utf-8") as reader:
                    lines = reader.readlines()
                    for line in lines:
                        # print(line)
                        lines_number += 1
    print(lines_number, "-number")


list_python_files('B:\ds_ai')
