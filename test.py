
def extract_number_after_keyword(input, keyword):
    index = input.find(keyword)
    if index != -1:
        remaining_str = input[index + len(keyword) + 1:]
        remaining_str = remaining_str[:remaining_str.find(" ")]
        if remaining_str:
            if remaining_str[0] == '-':
                numberStr = '-' + ''.join(char for char in remaining_str[1:] if char.isdigit())
            else:
                numberStr = ''.join(char for char in remaining_str if char.isdigit())
            if numberStr:
                print(f"Extract: {keyword}, Number:{numberStr}")
                return int(numberStr)
    return -1

line = "-url 0 -pitch 0 -rsize 1"
pitch = extract_number_after_keyword(line, "-pitch")
print(pitch)