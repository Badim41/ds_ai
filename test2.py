import os
import sys
from IPython.display import display, FileLink

file = sys.argv[1]
if os.path.exists(file):
    print("exists")
else:
    print("not exists")

file_link = FileLink(file)
display(file_link)

print("done")
