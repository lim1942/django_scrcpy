from h26x_extractor.nalutypes import SPS
from bitstring import BitStream
import time


a = b'B\xc0\x1e\x8dh\x16\x05\xbe^\x01\xe1\x10\x8d@\x00\x00\x00\x01h\xce\x01\xa85\xc8'
a = BitStream(a)
aa = time.time()
sps = SPS(a, True)
print(time.time()-aa)
# sps.print_verbose()