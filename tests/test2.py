import os
import signal
import subprocess
import time

cmd1 = "adb -s OROZ7LZ5PJY5ZTI7 push E:\\work\\django_scrcpy\\asynch\\scrcpy-server-v1.24 /data/local/tmp/scrcpy-server.jar"
cmd2 = "adb -s OROZ7LZ5PJY5ZTI7 shell CLASSPATH=/data/local/tmp/scrcpy-server.jar app_process / com.genymobile.scrcpy.Server 1.24 log_level=info max_size=720 bit_rate=8000000 max_fps=25 lock_video_orientation=-1 tunnel_forward=true crop= control=true display_id=0 show_touches=false stay_awake=True codec_options= encoder_name=OMX.google.h264.encoder power_off_on_close=false raw_video_stream=false send_frame_meta=True"

def open_process(command):
    return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)

# p1 = open_process(cmd1)
# stdout, stderr = p1.communicate()
# print(stdout)

p2 = open_process(f"{cmd1} && {cmd2}")
# print(p2.pid)
time.sleep(20)
print('o', p2.pid)
p2.terminate()
print('----')
# time.sleep(10)
# os.kill(p2.pid)
# print('t')
time.sleep(30000)
