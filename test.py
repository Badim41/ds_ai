x = 1980
y = 1080
scale_factor = (500000 / (x * y)) ** 0.5
x = int(x * scale_factor)
y = int(y * scale_factor)
if not x % 64 == 0:
    x = ((x // 64) + 1) * 64
if not y % 64 == 0:
    y = ((y // 64) + 1) * 64
print("X:", x, "Y:", y)