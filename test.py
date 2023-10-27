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
import re

# print(round(10 / 3, 4))


# def add_0(inputs):
#     output = []
#     for input in inputs:
#         # print(len(input[input.find("."):]))
#         if not "." in input:
#             output.append(input + ".00")
#             continue
#         if len(input[input.find("."):]) < 3:
#             output.append(input + "0")
#         else:
#             output.append(input)
#     return output
#
#
# # print(len("     1.05"))
# input_str1, input_str1_1, input_str1_2, input_str2, input_str2_1, input_str2_2 = input(), input(), input(), input(), input(), input()
# # Наименование изделия   Цена  Вес/Кол.   ВСЕГО
# # -------------------- ------- -------- ---------
# # Печенье               109.99     1.05    115.49
# # Молоко                 67.00     1.00     67.00
# # -------------------- ------- -------- ---------
# # ИТОГО                                    182.49
# result_1 = str(round(float(input_str1_1) * float(input_str1_2), 2))
# result_2 = str(round(float(input_str2_1) * float(input_str2_2), 2))
# input_str1_1, input_str1_2, input_str2_1, input_str2_2, result_1, result_2 = add_0([input_str1_1, input_str1_2, input_str2_1, input_str2_2, result_1, result_2])
# print("Наименование изделия   Цена  Вес/Кол.   ВСЕГО   ")
# print("-------------------- ------- -------- ---------")
# print("{:<20}".format(input_str1), "{:>7}".format(input_str1_1), "{:>8}".format(input_str1_2),
#       "{:>9}".format(result_1))
# print("{:<20}".format(input_str2), "{:>7}".format(input_str2_1), "{:>8}".format(input_str2_2),
#       "{:>9}".format(result_2))
# print("-------------------- ------- -------- ---------")
# result_final = add_0([str(float(result_1) + float(result_2))])[0]
# print("ИТОГО", "{:>41}".format(result_final))


# input_number = int(input())
# print((input_number - input_number ** 2) ** int(input()))


# input_int_1, input_int_2 = int(input()), int(input())
# print(int(input_int_2 / input_int_1))


# input_int_1, input_int_2 = int(input()), int(input())
# print(input_int_2 % input_int_1)


# input_int_1, input_int_2, input_int_3 = int(input()), int(input()), int(input())
# print(input_int_1 * 0.15 + input_int_2 * 0.15 + input_int_3 * 0.15)

# km, benzin_spend, benzin_cost = float(input()), float(input()), float(input())
# litrov_benzina = km / 100
# print(round(litrov_benzina * benzin_spend * benzin_cost * 2, 3))


# input_ints = [int(input()), int(input()), int(input())]
# result = 0
# for integer in input_ints:
#     if integer % 2 == 1:
#         result += 1
#     result += integer // 2
# print(result)

# input_int = int(input())
# print(input_int * int(str(input_int)[::-1]))

# str ="--opit-- itop"
# str = re.sub(r"--.*?--", '', str)
# print(str)

# def write_in_discord(text):
#     if text == "" or text is None:
#         print("пустое")
#         return
#     if len(text) < 1:
#         print(text)
#     else:
#         while not text == "":
#             text_part = text[:text.find("||") + 2]
#             text = text[text.find("||") + 2:]
#             text_part += text[:text.find("||") + 2]
#             text = text[text.find("||") + 2:]
#             if "```" in text_part:
#                 if len(text_part) > 1990:
#                     while text_part.find("```") > 1990:
#                         print(text_part[:1990], end="")
#                         text_part = text_part[1990:]
#             while not len(text_part) == 0:
#                 print(text_part[:1990], end="")
#                 text_part = text_part[1990:]
