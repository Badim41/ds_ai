color = input()
if color == "W":
    time_has = 300
else:
    time_has = 240

steps = int(input())
if steps > 60:
    time_has += (steps - 59) * 3

time_spent = 0
time_spent_str = input().split(" ")
for time in time_spent_str:
    time_spent += int(time)
if time_has - time_spent >= 0:
    print(time_has - time_spent)
else:
    print("-1")