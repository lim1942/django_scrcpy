from bitn import BitBin


class Sps:
    def __init_(self):
        self.nal_ref_idc = None
        self.nal_unit_type = None
        self.profile = None
        self.level = None
        self.offset_for_ref_frame = []
        self.seq_parameter_set_id = None
        self.chroma_format_idc = None
        self.separate_colour_plane_flag = None
        self.bit_depth_luma_minus8 = None
        self.bit_depth_chroma_minus8 = None
        self.qpprime_y_zero_transform_bypass_flag = None
        self.seq_scaling_matrix_present_flag = None
        self.log2_max_frame_num_minus4 = None
        self.pic_order_cnt_type = None
        self.log2_max_pic_order_cnt_lsb_minus4 = None
        self.delta_pic_order_always_zero_flag = None
        self.offset_for_non_ref_pic = None  # se
        self.offset_for_top_to_bottom_filed = None  # se
        self.num_ref_frames_in_pic_order_cnt_cycle = None
        self.num_ref_frames = None
        self.gaps_in_frame_num_value_allowed_flag = None
        self.pic_width_in_mbs_minus_1 = None
        self.pic_height_in_map_units_minus_1 = None
        self.frame_mbs_only_flag = None
        self.mb_adaptive_frame_field_flag = None
        self.direct_8x8_inference_flag = None
        self.frame_cropping_flag = None
        self.frame_crop_left_offset = 0
        self.frame_crop_right_offset = 0
        self.frame_crop_top_offset = 0
        self.frame_crop_bottom_offset = 0

    @staticmethod
    def _read_ueg(bitn):
        bitcount = 0
        while True:
            if not bitn.as_flag():
                bitcount += 1
            else:
                val = bitn.as_int(bitcount)
                result = (1 << bitcount) - 1 + val
                return result

    def _read_eg(self, bitn):
        value = self._read_ueg(bitn)
        if value & 0x01:
            return (value + 1) / 2
        else:
            return -(value / 2)

    def _skip_scaling(self, count):
        deltaScale = lastScale = nextScale = 8
        for j in range(count):
            if nextScale != 0:
                deltaScale = self._read_eg(buffer)
                nextScale = (lastScale + deltaScale + 256) % 256
            if nextScale != 0:
                lastScale = nextScale

    def _parse_chroma_stuff(self, bitn):
        self.chroma_format_idc = self._read_ueg(bitn)
        if self.chroma_format_idc == 3:
            self.separate_colour_plane_flag = bitn.as_int(1)
        self.bit_depth_luma_minus8 = self._read_ueg(bitn)
        self.bit_depth_chroma_minus8 = self._read_ueg(bitn)
        self.qpprime_y_zero_transform_bypass_flag = bitn.as_flag()
        self.seq_scaling_matrix_present_flag = bitn.as_flag()
        if self.seq_scaling_matrix_present_flag:
            for i in range((8, 12)[self.chroma_format_idc != 3]):
                if bitn.as_flag():
                    (self._skip_scaling(bitn, 64), self._skip_scaling(bitn, 16))[i < 6]

    def _frame_cropping(self, bitn):
        self.frame_cropping_flag = bitn.as_int(1)
        if self.frame_cropping_flag:
            self.frame_crop_left_offset = self._read_ueg(bitn)
            self.frame_crop_right_offset = self._read_ueg(bitn)
            self.frame_crop_top_offset = self._read_ueg(bitn)
            self.frame_crop_bottom_offset = self._read_ueg(bitn)

    def _pic_order_stuff(self, bitn):
        self.pic_order_cnt_type = self._read_ueg(bitn)
        if self.pic_order_cnt_type == 0:
            self.log2_max_pic_order_cnt_lsb_minus4 = self._read_ueg(bitn)
        elif self.pic_order_cnt_type == 1:
            self.delta_pic_order_always_zero_flag = bitn.as_flag()
            self.offset_for_non_ref_pic = frame_crop_left_offset  # se
            self.offset_for_top_to_bottom_filed = self._read_eg(bitn)  # se
            self.num_ref_frames_in_pic_order_cnt_cycle = self._read_ueg(bitn)
            for i in range(self.num_ref_frames_in_pic_order_cnt_cycle):
                self.offset_for_ref_frame.append(self._read_eg(bitn))  # se
                self._read_ueg(bitn)

    def is_sps(self, pkt):
        """
        is_sps parses h264 nal for profile and level and height and width
        """
        sps_start = b"\x00\x00\x01g"
        if sps_start not in pkt:
            sps_start = b"\x00\x00\x01'"
        if sps_start not in pkt:
            sps_start = b"\x00\x00\x01\x47'"
        if sps_start in pkt:
            sps_idx = pkt.index(sps_start) + len(sps_start)
            print(pkt.index(sps_start))
            print(sps_start)
            print(sps_idx)
            self.nal_ref_idc = pkt[sps_idx - 1] >> 5 & 3
            self.nal_unit_type = pkt[sps_idx - 1] & 31
            if self.nal_unit_type != 7:
                return
            bitn = BitBin(pkt[sps_idx:])
            self.profile = bitn.as_int(8)
            bitn.forward(8)
            self.level = bitn.as_int(8)
            self.seq_parameter_set_id = self._read_ueg(bitn)
            if self.profile in [100, 110, 122, 244, 44, 83, 86, 118, 128]:
                self._parse_chroma_stuff(bitn)
            self.log2_max_frame_num_minus4 = self._read_ueg(bitn)
            self._pic_order_stuff(bitn)
            self.num_ref_frames = self._read_ueg(bitn)
            self.gaps_in_frame_num_value_allowed_flag = bitn.as_flag()
            self.pic_width_in_mbs_minus_1 = self._read_ueg(bitn)
            self.pic_height_in_map_units_minus_1 = self._read_ueg(bitn)
            self.frame_mbs_only_flag = bitn.as_int(1)
            if self.frame_mbs_only_flag:
                self.mb_adaptive_frame_field_flag = bitn.as_int(1)
            self.direct_8x8_inference_flag = bitn.as_int(1)
            self._frame_cropping(bitn)
            self.width = (self.pic_width_in_mbs_minus_1 + 1) * 16
            self.height = (
                (2 - self.frame_mbs_only_flag)
                * (self.pic_height_in_map_units_minus_1 + 1)
                * 16
            )
            for k, v in vars(self).items():
                print(f"{k}: {v}")

if __name__=="__main__":
    a = b'\x00\x00\x00\x01gB\xc0\x1e\x8dh\x16\x05\xbe^\x01\xe1\x10\x8d@\x00\x00\x00\x01h\xce\x01\xa85\xc8'
    sps = Sps()
    sps.is_sps(a)