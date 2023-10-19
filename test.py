str = "1 ||123456|| 2 ||123456|| 3 ||123456|| 4 ||123456||"
pieces = []
while "||" in str:
    parts = str.split("||")
    parts.remove(parts[1])
    part = ''.join(parts)
print(str)