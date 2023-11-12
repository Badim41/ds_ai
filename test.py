import pyrubberband as pyrb

y, sr = sf.read(input_file)
y_stretch = pyrb.time_stretch(y, sr, speed_factor)
sf.write(input_file, y_stretch, sr)