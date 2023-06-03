import datetime


DEF SC_PACKET_FLAG_CONFIG = (1 << 63)
DEF SC_PACKET_FLAG_KEY_FRAME = (1 << 62)
DEF SC_PACKET_PTS_MASK = (SC_PACKET_FLAG_KEY_FRAME - 1)
cdef AVRational RECORD_TIME_BASE = {"num":1, "den":1000000}


cdef const AVOutputFormat* find_muxer(const char *name):
    cdef bint high_api = LIBAVFORMAT_VERSION_INT >= AV_VERSION_INT(58, 9, 100)
    cdef const AVOutputFormat *oformat = NULL
    cdef void *opaque = NULL
    while True:
        if high_api:
             oformat = av_muxer_iterate(&opaque)
        else:
            oformat = av_oformat_next(oformat)
        if (not oformat) or (name in oformat.name.split(',')):
            break
    return oformat


cdef class Recorder(object):
    def __cinit__(self, const char *muxer_name, const char *filename, bint has_audio):
        # open a container
        self.container = avformat_alloc_context()
        self.container.oformat = <AVOutputFormat *>find_muxer(muxer_name)
        avio_open(&self.container.pb, filename, AVIO_FLAG_WRITE)
        av_dict_set(&self.container.metadata, "comment","Recorded by django_scrcpy", 0)
        # has audio
        self.has_audio  = has_audio
        self.pts_origin = AV_NOPTS_VALUE
        self.pts_last  = AV_NOPTS_VALUE

    def __init__(self, *arg, **kwargs) -> None:
        self.start_time = datetime.datetime.now()
        self.finish_time = None

    @property
    def start_time(self):
        return self.start_time

    @property
    def finish_time(self):
        return self.finish_time   

    cdef uint32_t read32be(self, const uint8_t *data):
        return <uint32_t>((data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3])

    cdef uint64_t read64be(self, const uint8_t *data):
        cdef uint64_t msb = self.read32be(data)
        cdef uint32_t lsb = self.read32be(&data[4])
        return (<uint64_t> (msb << 32)) | lsb

    cdef void init_packet(self, AVPacket * packet, const uint8_t *pts, int length, const uint8_t *data):
        cdef uint64_t pts_flags = self.read64be(pts)
        av_new_packet(packet, length)
        memcpy(packet.data, data, packet.size)
        if (SC_PACKET_FLAG_CONFIG & pts_flags):
            packet.pts = AV_NOPTS_VALUE
        else:
            packet.pts = pts_flags & SC_PACKET_PTS_MASK
        if pts_flags & SC_PACKET_FLAG_KEY_FRAME:
            packet.flags |=  AV_PKT_FLAG_KEY
        packet.dts = packet.pts

    cdef void packet_merger_init(self):
        self.merger.config = NULL

    cdef void packet_merger_merge(self, AVPacket *packet):
        cdef bint is_config = packet.pts == AV_NOPTS_VALUE
        cdef size_t config_size
        cdef size_t media_size
        if is_config:
            free(self.merger.config)
            self.merger.config = <uint8_t *> malloc(packet.size)
            if not self.merger.config:
                print("recorder.c: malloc error")
            memcpy(self.merger.config, packet.data, packet.size)
            self.merger.config_size = packet.size
        elif self.merger.config:
            config_size = self.merger.config_size
            media_size = packet.size
            if av_grow_packet(packet, config_size):
                print("recorder.c: av_grow_packet errorn")
            memmove(packet.data + config_size, packet.data, media_size)
            memcpy(packet.data, self.merger.config, config_size)
            free(self.merger.config)
            self.merger.config = NULL

    cdef void packet_merger_destroy(self):
        free(self.merger.config)

    
    cdef AVCodecID get_avcodec_id(self, const uint8_t *codec_name):
        cdef uint32_t avcodec_id_u32t = self.read32be(codec_name)
        if avcodec_id_u32t == 0x68323634:
            return AVCodecID.AV_CODEC_ID_H264
        elif avcodec_id_u32t == 0x68323635:
            return AVCodecID.AV_CODEC_ID_HEVC
        elif avcodec_id_u32t == 0x00617631:
            return AVCodecID.AV_CODEC_ID_AV1            
        elif avcodec_id_u32t == 0x6f707573:
            return AVCodecID.AV_CODEC_ID_OPUS
        elif avcodec_id_u32t == 0x00616163:
            return AVCodecID.AV_CODEC_ID_AAC
        elif avcodec_id_u32t == 0x00726177:
            return AVCodecID.AV_CODEC_ID_PCM_S16LE
        else:
            return AVCodecID.AV_CODEC_ID_NONE

    cpdef void add_video_stream(self, const uint8_t *codec_name, const uint8_t *width, const uint8_t *height):
        cdef uint32_t width_int = self.read32be(width)
        cdef uint32_t height_int = self.read32be(height)
        # 1.get codec id 
        cdef  AVCodecID video_codec_id = self.get_avcodec_id(codec_name)
        # 2.get codec and set codec_ctx
        cdef const AVCodec *video_codec = avcodec_find_decoder(video_codec_id)
        cdef AVCodecContext *video_codec_ctx = avcodec_alloc_context3(video_codec)
        video_codec_ctx.flags |= AV_CODEC_FLAG_LOW_DELAY
        video_codec_ctx.width = width_int
        video_codec_ctx.height = height_int
        video_codec_ctx.pix_fmt = AVPixelFormat.AV_PIX_FMT_YUV420P
        if (avcodec_open2(video_codec_ctx, video_codec, NULL) < 0):
            print("recorder.c: demuxer could not open video codec")
            return
        # 3.attach codec_ctx to container get video_stream
        cdef AVStream *video_stream = avformat_new_stream(self.container, video_codec_ctx.codec)
        avcodec_parameters_from_context(video_stream.codecpar, video_codec_ctx)
        
    cpdef void add_audio_stream(self, const uint8_t *codec_name):
        # 1.get codec id 
        cdef  AVCodecID audio_codec_id = self.get_avcodec_id(codec_name)
        # 2.get codec and set codec_ctx
        cdef const AVCodec *audio_codec = avcodec_find_decoder(audio_codec_id)
        cdef AVCodecContext *audio_codec_ctx = avcodec_alloc_context3(audio_codec)
        audio_codec_ctx.flags |= AV_CODEC_FLAG_LOW_DELAY
        audio_codec_ctx.channel_layout = AV_CH_LAYOUT_STEREO
        audio_codec_ctx.channels = 2
        audio_codec_ctx.sample_rate = 48000
        if (avcodec_open2(audio_codec_ctx, audio_codec, NULL) < 0):
            print("recorder.c: demuxer could not open audio codec")
            return
         # 3.attach codec_ctx to container get video_stream
        cdef AVStream *audio_stream = avformat_new_stream(self.container, audio_codec_ctx.codec)
        avcodec_parameters_from_context(audio_stream.codecpar, audio_codec_ctx)

    cpdef void write_video_header(self, const uint8_t *pts, int length, const uint8_t *data):
        self.video_packet = av_packet_alloc()
        self.packet_merger_init()
        self.init_packet(self.video_packet, pts, length, data)
        self.packet_merger_merge(self.video_packet)
        cdef uint8_t *extradata = <uint8_t *> av_malloc(self.video_packet.size * sizeof(uint8_t))
        memcpy(extradata, self.video_packet.data, self.video_packet.size)
        self.container.streams[0].codecpar.extradata = extradata
        self.container.streams[0].codecpar.extradata_size = self.video_packet.size
        av_packet_free(&self.video_packet)

    cpdef void write_audio_header(self, const uint8_t *pts, int length, const uint8_t *data):
        self.audio_packet = av_packet_alloc()
        self.init_packet(self.audio_packet, pts, length, data)
        cdef uint8_t *extradata = <uint8_t *> av_malloc(self.audio_packet.size * sizeof(uint8_t))
        memcpy(extradata, self.audio_packet.data, self.audio_packet.size)
        self.container.streams[1].codecpar.extradata = extradata
        self.container.streams[1].codecpar.extradata_size = self.audio_packet.size
        av_packet_free(&self.audio_packet)

    cpdef void write_header(self):
        cdef bint ok = (avformat_write_header(self.container, NULL) >= 0)
        if not ok:
            print("failed write header !!!!")

    cpdef void write_video_packet(self, const uint8_t *pts, int length, const uint8_t *data):
        self.video_packet = av_packet_alloc()
        self.init_packet(self.video_packet, pts, length, data)
        if self.pts_origin == AV_NOPTS_VALUE:
            self.pts_origin = self.video_packet.pts
        # config packet
        if self.video_packet.pts == AV_NOPTS_VALUE:
            self.packet_merger_merge(self.video_packet)
        # data packet
        else:
            self.pts_last = self.video_packet.pts
            self.video_packet.stream_index = 0
            self.video_packet.pts -= self.pts_origin
            self.video_packet.dts = self.video_packet.pts
            self.packet_merger_merge(self.video_packet)
            if self.previous_video_packet:
                self.previous_video_packet.duration = self.video_packet.pts- self.previous_video_packet.pts
                av_packet_rescale_ts(self.previous_video_packet, RECORD_TIME_BASE, self.container.streams[0].time_base)
                if av_interleaved_write_frame(self.container, self.previous_video_packet)<0:
                    print("recorder.c: Failed to write video packet")
                av_packet_free(&self.previous_video_packet)
            self.previous_video_packet = av_packet_clone(self.video_packet)
            av_packet_free(&self.video_packet)

    cpdef void write_audio_packet(self, const uint8_t *pts, int length, const uint8_t *data):
        self.audio_packet = av_packet_alloc()
        self.init_packet(self.audio_packet, pts, length, data)
        if self.pts_origin == AV_NOPTS_VALUE:
            self.pts_origin = self.audio_packet.pts
        self.audio_packet.stream_index = 1
        self.audio_packet.pts -= self.pts_origin
        self.audio_packet.dts = self.audio_packet.pts
        av_packet_rescale_ts(self.audio_packet, RECORD_TIME_BASE, self.container.streams[1].time_base)
        if av_interleaved_write_frame(self.container, self.audio_packet)<0:
            print("recorder.c: Failed to write audio packet")
        av_packet_free(&self.video_packet)

    cpdef int close_container(self):
        if self.previous_video_packet:
            self.previous_video_packet.duration = 100000
            av_packet_rescale_ts(self.previous_video_packet, RECORD_TIME_BASE, self.container.streams[0].time_base)
            av_interleaved_write_frame(self.container, self.previous_video_packet)
            av_packet_free(&self.previous_video_packet)
        if av_write_trailer(self.container) <0:
            print("recorder.c: Failed to write trailer")
        avio_close(self.container.pb)
        avformat_free_context(self.container)
        self.finish_time = datetime.datetime.now()
        return <int> ((self.pts_last - self.pts_origin)/1000000)
