input_int = list(input())
if not len(input_int) == 16:
    print("No")
sum_num = 0
i = 0
for num in input_int:
    i += 1
    num = int(num)
    if i % 2 == 0:
        sum_num += num
        continue
    num *= 2
    if num > 9:
        num_new = 0
        for num_in_2num in list(str(num)):
            num_new += int(num_in_2num)
        num = num_new
    sum_num += num
if sum_num % 10 == 0:
    print("Yes")
else:
    print("No")
