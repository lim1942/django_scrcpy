import struct
import recorder

recorder_obj = recorder.Recorder("mp4", 'test.mp4', False)
# # print(a.add_video_stream('h264', 1920,1080))
# # print(a.add_audio_stream('opus'))
# a.test(b'111122')
f = open('raw.h264', 'rb')
video_codec = f.read(4).replace(b'\x00', b'').decode('ascii')
w, h = struct.unpack('>ii', f.read(8))
recorder_obj.add_video_stream(video_codec, w, h)
audio_codec = f.read(4).replace(b'\x00', b'').decode('ascii')
if audio_codec:
    recorder_obj.add_audio_stream(audio_codec)

pts = struct.unpack('>Q', f.read(8))[0]
length = struct.unpack('>L', f.read(4))[0]
data = f.read(length)
recorder_obj.write_video_header(pts, length, data)
recorder_obj.write_header()
while True:
    try:
        pts = struct.unpack('>Q', f.read(8))[0]
        length = struct.unpack('>L', f.read(4))[0]
        data = f.read(length)
        recorder_obj.write_video_packet(pts, length, data)
    except:
        break

print(recorder_obj.close_container())
print(recorder_obj.start_time)
print(recorder_obj.finish_time)
del recorder_obj
