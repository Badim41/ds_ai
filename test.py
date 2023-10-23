import subprocess

audio1 = "/kaggle/working/123.mp3"
audio2 = "/kaggle/working/123.mp3"
output_file = "combined3.m4a"

ffmpeg_command = (
    f'ffmpeg -i {audio1} -i {audio1} -filter_complex "[0:a][1:a]amerge=inputs=2[aout]" -map "[aout]" -c:a aac -strict experimental -q:a 1 {output_file} -y'
)

subprocess.run(ffmpeg_command, shell=True)