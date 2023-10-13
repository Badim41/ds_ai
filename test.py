from pydub import AudioSegment

audio = AudioSegment.from_file("C:/Users/as280/Downloads/rawData4 [vocals].wav", format="wav")
# делим аудиофайл на две части
half_length = len(audio) // 2
audio_part1 = audio[:half_length]
audio_part2 = audio[half_length:]
audio_part1.export("0.mp3", format="mp3")
audio_part2.export("1.mp3", format="mp3")
result = AudioSegment.from_file("0.mp3", format="mp3") + AudioSegment.from_file("1.mp3", format="mp3")
result.export("all.mp3", format="mp3")