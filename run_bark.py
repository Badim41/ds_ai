import argparse
from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
from pydub import AudioSegment

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-tts', '--tts', type=str, required=True)
    parser.add_argument('-language', '--language', type=str, required=True)
    parser.add_argument('-output_file', '--output_file', type=str, required=True)
    parser.add_argument('-speaker', '--speaker', type=str, required=True)

    args = parser.parse_args()

    tts = args.tts
    language = args.language
    output_file = args.output_file
    speaker = args.speaker

    print("Bark_fun")
    try:

        speaker = language + "_speaker_" + str(speaker)
        audio_array = generate_audio(tts, history_prompt=speaker)
        write_wav("temp.wav", SAMPLE_RATE, audio_array)
        audio = AudioSegment.from_wav("temp.wav")
        audio.export(output_file, format="mp3")
    except Exception as e:
        raise f"Ошибка при команде Bark:{e}"
