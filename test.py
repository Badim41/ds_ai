
def extract_double_after_keyword(input, keyword):
    index = input.find(keyword)

    if index != -1:
        remaining_str = input[index + len(keyword) + 1:]
        remaining_str = remaining_str[:remaining_str.find(" ")]
        numberStr = ''.join(char for char in remaining_str if char.isdigit() or char == '.')

        try:
            if numberStr:
                return float(numberStr.replace(',', '.'))
        except ValueError as e:
            pass

line = "-url 0.2 -pitch 0.6 -rsize 1.2"
pitch = extract_double_after_keyword(line, "-pitch")
print(pitch)