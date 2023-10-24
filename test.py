# import subprocess
#
# audio1 = "/kaggle/working/123.mp3"
# audio2 = "/kaggle/working/123.mp3"
# output_file = "combined3.m4a"
#
# ffmpeg_command = (
#     f'ffmpeg -i {audio1} -i {audio1} -filter_complex "[0:a][1:a]amerge=inputs=2[aout]" -map "[aout]" -c:a aac -strict experimental -q:a 1 {output_file} -y'
# )
#
# subprocess.run(ffmpeg_command, shell=True)


# 2πR
# π^2 R
# V = (4/3) × π × r³
# S = 4πR^2
input_int = int(input())
P = 3.141592
formula_1 = 2 * P * input_int
formula_2 = input_int**2 * P
formula_3 = (4/3) * P * input_int**3
formula_4 = 4 * P * input_int**2
print(f"Длина окружности радиуса {input_int} равна {round(formula_1, 3)}\n\
Площадь круга радиуса {input_int} равна {round(formula_2, 3)}\n\
Объем шара радиуса {input_int} равен {round(formula_3, 3)}\n\
Площадь поверхности шара радиуса {input_int} равна {round(formula_4, 3)}")