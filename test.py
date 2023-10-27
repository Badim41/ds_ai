from pydub import AudioSegment


def speed_up_audio(input_file, speed_factor):
    audio = AudioSegment.from_file(input_file)
    sped_up_audio = audio.speedup(playback_speed=speed_factor)
    sped_up_audio.export(input_file, format="mp3")

input_file = "C:/Users/as280/Downloads/107.mp3"

speed_up_audio(input_file, 1.2)