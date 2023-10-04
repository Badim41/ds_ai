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

print(124 / 36**6)
print(1 / 17554695.96774194)
num = int("1" + ("0" * 24))
print(len(str(num)))

num_result = []
while num / 16 >= 1:
    num_result.append(str(int(num / 16)))
    num -= 16 * int(num / 16)
num_result.append(str(num))
num = ''.join(num_result)
print(num)
print(len(num))