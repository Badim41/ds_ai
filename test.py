from pydub import AudioSegment
import os

orig_song_path = "C:/Users/as280/Downloads/123.mp3"


result_vocals = AudioSegment.from_file(orig_song_path, format="mp3") + AudioSegment.from_file(orig_song_path,format="mp3")
result_vocals.export(os.path.dirname(orig_song_path) + "/vocals.mp3", format="mp3")
print(os.path.dirname(orig_song_path))