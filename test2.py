import os
import sys
from IPython.display import display, FileLink
file = sys.argv[1]
if os.path.exists(file):
    print("exists")
else:
    print("not exists")
FileLink(file)
display(FileLink(file))
print("done")