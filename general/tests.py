# High level usage using `spawn`
from winpty import PtyProcess

proc = PtyProcess.spawn('python')
proc.write('print("hello, world!")\r\n')
proc.write('exit()\r\n')
while proc.isalive():
	print(proc.readline())

# Low level usage using the raw `PTY` object
from winpty import PTY

# Start a new winpty-agent process of size (cols, rows)
cols, rows = 80, 25
process = PTY(cols, rows)

# Spawn a new console process, e.g., CMD
process.spawn(br'C:\windows\system32\cmd.exe')

# Read console output (Unicode)
process.read()

# Write input to console (Unicode)
process.write(b'Text')

# Resize console size
new_cols, new_rows = 90, 30
process.set_size(new_cols, new_rows)

# Know if the process is alive
alive = process.isalive()

# End winpty-agent process
del process