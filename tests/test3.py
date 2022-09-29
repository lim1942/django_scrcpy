from bitstring import BitStream
from h26x_extractor.nalutypes import SPS, PPS

a = b'\x1e\x8dh\x16\x05\xbe^\x01\xe1\x10\x8d@'
# a = b'\x00\x00\x01gB\xc0\x1e\x8dh\x16\x05\xbe^\x01\xe1\x10\x8d@'
a = BitStream(a)
b = b'\xce\x01\xa85\xc8'
# b = b'\x00\x00\x00\x01h\xce\x01\xa85\xc8'
b = BitStream(b)


c = SPS(a, True)
c.print_verbose()


# d = PPS(b, True)
# d.print_verbose()
