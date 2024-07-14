from mtranslate import translate
class Languages:
    ru = "ru"
    en = "en"
    zh = "zh"
    es = "es"
    hi = "hi"
    ar = "ar"
    bn = "bn"
    pt = "pt"
    fa = "fa"
    de = "de"
    it = "it"
    ja = "ja"

async def translate_text(text, target_lang):
    def contains_only_english_chars(input_string):
        return all('a' <= char.lower() <= 'z' for char in input_string if char.isalpha())

    try:
        if contains_only_english_chars(text) and target_lang == Languages.en:
            print("only en")
            return text

        translated_text = translate(text, target_lang)
        return translated_text

    except Exception as e:
        print("error", e)
        return text