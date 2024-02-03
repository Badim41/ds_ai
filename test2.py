import json


def get_elevenlabs_voice_id_by_name(voice_name):
    with open('voices.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    voice = next((v for v in data["voices"] if v["name"] == voice_name), None)
    return voice["voice_id"] if voice else None

print(get_elevenlabs_voice_id_by_name("Adam"))