x = 2
y = 1
scale_factor = (589824 / x*y) ** 0.5
x = int(x * scale_factor)
y = int(y * scale_factor)

print(x, y)