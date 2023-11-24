def run_gpt(prompt, mode="fast"):
    import subprocess

    # Формируем команду
    command = f'python gpt.py -prompt "{prompt}" -mode "{mode}"'

    # Запускаем процесс
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)

    # Итератор для чтения строк из потока вывода
    for line in iter(process.stdout.readline, ''):
        # print(line, end='')
        if "Answer" in line:
            process.terminate()
            print(line[7:], end='')

    # Ждем завершения процесса
    process.communicate()

    # Если нужно обработать ошибки
    if process.returncode != 0:
        pass

run_gpt("Привет!")