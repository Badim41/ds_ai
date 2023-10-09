import os
import zipfile

from IPython.lib.display import FileLink

print("test")
output_path = "caversAI"
audio_paths = ["caversAI/audio_links.txt"]
with zipfile.ZipFile(f'{os.path.basename(output_path)[:-4]}.zip', 'w') as zipf:
    zipf.write(audio_paths[0], arcname='1')
FileLink(f'{os.path.basename(output_path)[:-4]}')