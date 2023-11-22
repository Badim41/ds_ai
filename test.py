import json




def get_all_voices(json_data):
    voices_with_gender = [(voice["name"] + " ["  + voice["labels"]["gender"][0].upper().replace("F","Ж").replace("M","М") + "]") for voice in json_data["voices"]]

    return voices_with_gender


# Load JSON data from file
with open('new.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

get_all_voices = get_all_voices(data)
print(get_all_voices)

