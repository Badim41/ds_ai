# nums = []
#
#
# def count_variants(len):
#     number_variants = 1
#     for i in range(1 + len):
#         if i < 1:
#             continue
#         number_variants *= i
#         # print(number_variants)
#     return number_variants
#
#
# print(count_variants(16) * (8*12+5))
import configparser
import multiprocessing
import os
import time

# print(124 / 36**6)
# print(1 / 17554695.96774194)
# num = int("1" + ("0" * 24))
# print(len(str(num)))
#
# num_result = []
# while num / 16 >= 1:
#     num_result.append(str(int(num / 16)))
#     num -= 16 * int(num / 16)
# num_result.append(str(num))
# num = ''.join(num_result)
# print(num)
# print(len(num))
spokenText = "протокол 13 -url https://www.youtube.com/watch?v=TFtjM6piFPY \nпротокол 13 -url https://www.youtube.com/watch?v=TFtjM6piFPY \nпротокол 13 -url https://www.youtube.com/watch?v=TFtjM6piFPY \nпротокол 13 -url https://www.youtube.com/watch?v=TFtjM6piFPY"

config = configparser.ConfigParser()


def set_config_static_values(key, value):
    config.read('config.ini')
    config.set('Values', key, value)
    # Сохранение
    with open('config.ini', 'w') as configfile:
        config.write(configfile)



def createAICaver(ctx):
    global spokenText
    message = spokenText
    lines = message.split("\n")
    if not os.path.exists("caversAI/audio_links.txt"):
        with open("caversAI/audio_links.txt", "w"):
            pass

    with open("caversAI/audio_links.txt", "a") as writer:
        for line in lines:
            writer.write(line + "\n")
    pool = multiprocessing.Pool(processes=1)
    pool2 = multiprocessing.Pool(processes=1)
    pool.apply_async(prepare_audio_process_cuda_0, (ctx,))
    pool2.apply_async(play_audio_process, (ctx,))
    pool.close()
    pool2.close()
    pool.join()
    pool2.join()


def prepare_audio_process_cuda_0(ctx):
    while True:
        try:
            with open("caversAI/audio_links.txt") as reader:
                line = reader.readline()
                if not line == "" and not line is None:
                    # youtube_dl_path = "youtube-dl.exe"
                    if "https://youtu.be/" not in line and "https://www.youtube.com/" not in line:
                        print("Ссылка не с YT")
                        remove_line_from_txt("caversAI/audio_links.txt", 1)
                        break

                    # url = line[line.index("https://"):].split()[0]
                    # if " " in url:
                    #     url = url[:url.index(" ")]

                    # command = f"{youtube_dl_path} {url} --max-filesize {video_length * 2 + 2}m --min-views 50000 --no-playlist --buffer-size 8K"
                    # if console_command_runner(command, ctx):
                    #     print("Условия выполнены")
                    # else:
                    #     print("Условия не выполнены")
                    #     remove_line_from_txt("caversAI/audio_links.txt", 1)
                    #     break

                    params = getCaverPrms(line, ctx)
                    params += " -cuda 0"
                    remove_line_from_txt("caversAI/audio_links.txt", 1)
                    print("запуск AICoverGen")
                    print(params, ctx)
                    time.sleep(5)
                    lines = []
                    with open("caversAI/queue.txt", "r") as reader:
                        lines = reader.readlines()
                    lines.append("path/path/file.mp3 -start 0 -time -1\n")
                    with open("caversAI/queue.txt", "w") as writer:
                        writer.writelines(lines)
                else:
                    print("Больше нет ссылок")
                    set_config_static_values("queue", "False")
                    break
        except (IOError, KeyboardInterrupt):
            pass


def remove_line_from_txt(file_path, delete_line):
    try:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        lines = []
        with open(file_path, "r") as reader:
            i = 1
            for line in reader:
                if i == delete_line:
                    print(f"Line removed: {line}")
                else:
                    lines.append(line)
                i += 1

        with open(file_path, "w") as writer:
            for line in lines:
                writer.write(line)
    except IOError as e:
        print(e)


def getCaverPrms(line, ctx):
    # SONG_INPUT
    url = "."
    if "-url" in line:
        if "https" in line:
            url = line[line.index("https"):]
            if " " in url:
                url = url[:url.index(" ")]

    # RVC_DIRNAME

    # PITCH_CHANGE
    pitch = 0
    if "-pitch" in line:
        pitch = extract_number_after_keyword(line, "-pitch")
        if pitch < -2 or pitch > 2:
            pitch = 0

    # время (не является аргументом для RVC)
    time = -1
    if "-time" in line:
        time = extract_number_after_keyword(line, "-time")
        if time < 0:
            time = -1

    # INDEX_RATE
    indexrate = 0.5
    if "-indexrate" in line:
        indexrate = extract_double_after_keyword(line, "-indexrate")
        if indexrate < 0 or indexrate > 1:
            indexrate = 0.5

    # RMS_MIX_RATE
    loudness = 0.2
    if "-loudness" in line:
        loudness = extract_double_after_keyword(line, "-loudness")
        if loudness < 0 or loudness > 1:
            loudness = 0.5

    # MAIN_VOCALS_VOLUME_CHANGE
    mainVocal = 0
    if "-vocal" in line:
        mainVocal = extract_number_after_keyword(line, "-vocal")
        if mainVocal < -20 or mainVocal > 0:
            mainVocal = 0

    # BACKUP_VOCALS_VOLUME_CHANGE
    backVocal = 0
    if "-bvocal" in line:
        backVocal = extract_number_after_keyword(line, "-bvocal")
        if backVocal < -20 or backVocal > 0:
            backVocal = 0

    # INSTRUMENTAL_VOLUME_CHANGE
    music = 0
    if "-music" in line:
        music = extract_number_after_keyword(line, "-music")
        if music < -20 or music > 0:
            music = 0

    # REVERB_SIZE
    roomsize = 0.2
    if "-roomsize" in line:
        roomsize = extract_double_after_keyword(line, "-roomsize")
        if roomsize < 0 or roomsize > 1:
            roomsize = 0.2

    # REVERB_WETNESS
    wetness = 0.1
    if "-wetness" in line:
        wetness = extract_double_after_keyword(line, "-wetness")
        if wetness < 0 or wetness > 1:
            wetness = 0.1

    # REVERB_DRYNESS
    dryness = 0.85
    if "-dryness" in line:
        dryness = extract_double_after_keyword(line, "-dryness")
        if dryness < 0 or dryness > 1:
            dryness = 0.85

    # начало
    start = 0
    if "-start" in line:
        start = extract_number_after_keyword(line, "-start")
        if start < 0:
            start = 0

    outputFormat = "mp3"

    return f"python src/main.py -i {url} -dir modelsRVC/voice -p {pitch} -ir {indexrate} -rms {loudness} -mv {mainVocal} -bv {backVocal} -iv {music} -rsize {roomsize} -rwet {wetness} -rdry {dryness} -start {start} -time {time} -oformat {outputFormat}"


def play_audio_process(ctx):
    set_config_static_values("queue", "True")
    while True:
        with open("caversAI/queue.txt", "r") as reader:
            line = reader.readline()
            if not line == "" and not line is None:
                print("Playing: " + line)
                print("2")
                params = getCaverPrms(line, ctx)
                time = extract_number_after_keyword(params, "-time")
                stop_milliseconds = extract_number_after_keyword(params, "-start")
                audio_path = line.split()[0]
                playSoundFile(audio_path, time, stop_milliseconds, ctx)
                remove_line_from_txt("caversAI/queue.txt", 1)
            else:
                config.read('config.ini')
                continue_process = config.getboolean('Values', 'queue')
                if not continue_process:
                    print("==============================================")
                    break


def extract_number_after_keyword(input, keyword):
    input = ''.join(char if char.isalnum() or char.isspace() else ' ' for char in input)
    index = input.find(keyword)

    if index != -1:
        start = index + len(keyword) + 1
        end = input.find(" ", start) if " " in input[start:] else len(input)
        numberStr = ''.join(char for char in input[start:end] if char.isdigit())

        if numberStr:
            return int(numberStr)

    return -1


def extract_double_after_keyword(input, keyword):
    input = ''.join(char if char.isalnum() or char.isspace() else ' ' for char in input)
    index = input.find(keyword)

    if index != -1:
        start = index + len(keyword) + 1
        end = input.find(" ", start) if " " in input[start:] else len(input)
        numberStr = ''.join(char for char in input[start:end] if char.isdigit() or char == '.')

        try:
            if numberStr:
                return float(numberStr.replace(',', '.'))
        except ValueError:
            pass

    return -1


def playSoundFile(audio_file_path, duration, start_seconds, ctx):
    print("PLAYING:", ctx, audio_file_path, duration, start_seconds)
    print("Аудио закончилось")


if __name__ == "__main__":
    createAICaver("context")
