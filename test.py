def extract_number_after_keyword(input, keyword):
    index = input.find(keyword)
    if index != -1:
        remaining_str = input[index + len(keyword) + 1:]
        if " " in remaining_str:
            remaining_str = remaining_str[:remaining_str.find(" ")]
        if remaining_str:
            if remaining_str[0] == '-':
                numberStr = '-' + ''.join(char for char in remaining_str[1:] if char.isdigit())
            else:
                numberStr = ''.join(char for char in remaining_str if char.isdigit())
            if numberStr:
                # await result_command_change(f"Extract: {keyword}, Number:{numberStr}", Color.GRAY)
                return int(numberStr)
    return -1

string = "Line removed: /kaggle/working/ds_ai/song_output/1777beb1f67/792658 (Фарадей Ver).mp3 -time -1 -start 0 -output all_files"
print(extract_number_after_keyword(string, "-time"))