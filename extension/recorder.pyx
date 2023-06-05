cdef uint64_t SC_PACKET_FLAG_CONFIG = (1 << 63)
cdef uint64_t SC_PACKET_FLAG_KEY_FRAME = (1 << 62)
cdef uint64_t SC_PACKET_PTS_MASK = (SC_PACKET_FLAG_KEY_FRAME - 1)
cdef AVRational RECORD_TIME_BASE = {"num":1, "den":1000000}


cdef class ByteSource(object):
    def __cinit__(self, data):
        self.ptr = data
        # Can very likely use PyBUF_ND instead of PyBUF_SIMPLE
        res = PyObject_GetBuffer(data, &self.view, PyBUF_SIMPLE)
        if not res:
            self.has_view = True
            self.ptr = <unsigned char *>self.view.buf
            self.length = self.view.len
            return
        raise TypeError('expected bytes, bytearray or memoryview')

    def __dealloc__(self):
        if self.has_view:
            PyBuffer_Release(&self.view)


cdef const AVOutputFormat* find_muxer(const char *name):
    cdef const AVOutputFormat *oformat = NULL
    cdef void *opaque = NULL
    while True:
        oformat = av_muxer_iterate(&opaque)
        assert oformat
        if name in oformat.name:
            break
    return oformat


cdef class Recorder(object):
    def __cinit__(self, const char *muxer_name, const char *filename, bint has_audio):
        self.has_finish = False
        # has audio
        self.has_audio  = has_audio
        # open a container
        self.container = avformat_alloc_context()
        self.container.oformat = <AVOutputFormat *>find_muxer(muxer_name)
        avio_open(&self.container.pb, filename, AVIO_FLAG_WRITE)
        av_dict_set(&self.container.metadata, "comment","Recorded by django_scrcpy", 0)
        # time info
        self.pts_origin = AV_NOPTS_VALUE
        self.pts_last  = AV_NOPTS_VALUE
        self.start_time = <long> time(NULL)

    @property
    def start_time(self):
        return self.start_time

    @property
    def finish_time(self):
        return self.finish_time   

    cdef void packet_merger_init(self):
        self.merger.config = NULL

    cdef void packet_merger_merge(self, AVPacket *packet):
        cdef bint is_config = packet.pts == AV_NOPTS_VALUE
        cdef size_t config_size
        cdef size_t media_size
        if is_config:
            free(self.merger.config)
            self.merger.config = <uint8_t *> malloc(packet.size)
            memcpy(self.merger.config, packet.data, packet.size)
            self.merger.config_size = packet.size
        elif self.merger.config:
            config_size = self.merger.config_size
            media_size = packet.size
            av_grow_packet(packet, config_size)
            memmove(packet.data + config_size, packet.data, media_size)
            memcpy(packet.data, self.merger.config, config_size)
            free(self.merger.config)
            self.merger.config = NULL

    cdef void packet_merger_destroy(self):
        free(self.merger.config)
    
    cdef AVCodecID get_avcodec_id(self, char *codec_name,):
        if strcmp(codec_name, "h264")==0:
            return AVCodecID.AV_CODEC_ID_H264
        elif strcmp(codec_name, "h265")==0:
            return AVCodecID.AV_CODEC_ID_HEVC
        elif strcmp(codec_name, "av1")==0:
            return AVCodecID.AV_CODEC_ID_AV1            
        elif strcmp(codec_name, "opus")==0:
            return AVCodecID.AV_CODEC_ID_OPUS
        elif strcmp(codec_name, "aac")==0:
            return AVCodecID.AV_CODEC_ID_AAC
        elif strcmp(codec_name, "raw")==0:
            return AVCodecID.AV_CODEC_ID_PCM_S16LE
        else:
            return AVCodecID.AV_CODEC_ID_NONE

    def add_video_stream(self, char *codec_name, int width, int height):
        # 1.get codec id 
        cdef  AVCodecID video_codec_id = self.get_avcodec_id(codec_name)
        # 2.get codec and set codec_ctx
        cdef const AVCodec *video_codec = avcodec_find_decoder(video_codec_id)
        self.video_codec_ctx = avcodec_alloc_context3(video_codec)
        self.video_codec_ctx.flags |= AV_CODEC_FLAG_LOW_DELAY
        self.video_codec_ctx.width = width
        self.video_codec_ctx.height = height
        self.video_codec_ctx.pix_fmt = AVPixelFormat.AV_PIX_FMT_YUV420P
        if (avcodec_open2(self.video_codec_ctx, video_codec, NULL) < 0):
            return False
        # 3.attach codec_ctx to container get video_stream
        cdef AVStream *video_stream = avformat_new_stream(self.container, self.video_codec_ctx.codec)
        avcodec_parameters_from_context(video_stream.codecpar, self.video_codec_ctx)
        return True
        
    def add_audio_stream(self, char *codec_name):
        # 1.get codec id 
        cdef  AVCodecID audio_codec_id = self.get_avcodec_id(codec_name)
        # 2.get codec and set codec_ctx
        cdef const AVCodec *audio_codec = avcodec_find_decoder(audio_codec_id)
        self.audio_codec_ctx = avcodec_alloc_context3(audio_codec)
        self.audio_codec_ctx.flags |= AV_CODEC_FLAG_LOW_DELAY
        self.audio_codec_ctx.channel_layout = AV_CH_LAYOUT_STEREO
        self.audio_codec_ctx.channels = 2
        self.audio_codec_ctx.sample_rate = 48000
        if (avcodec_open2(self.audio_codec_ctx, audio_codec, NULL) < 0):
            return False
         # 3.attach codec_ctx to container get video_stream
        cdef AVStream *audio_stream = avformat_new_stream(self.container, self.audio_codec_ctx.codec)
        avcodec_parameters_from_context(audio_stream.codecpar, self.audio_codec_ctx)
        return True

    def init_packet(self, bint is_video, uint64_t pts, int length, object data):
        packet = self.video_packet if is_video else self.audio_packet
        av_new_packet(packet, length)
        byte_source = ByteSource(data)
        memcpy(packet.data, byte_source.ptr, packet.size)
        del byte_source
        if (SC_PACKET_FLAG_CONFIG & pts):
            packet.pts = AV_NOPTS_VALUE
        else:
            packet.pts = pts & SC_PACKET_PTS_MASK
        if pts & SC_PACKET_FLAG_KEY_FRAME:
            packet.flags |=  AV_PKT_FLAG_KEY
        packet.dts = packet.pts

    def write_video_header(self, uint64_t pts, int length, object data):
        self.video_packet = av_packet_alloc()
        self.packet_merger_init()
        self.init_packet(True, pts, length, data)
        self.packet_merger_merge(self.video_packet)
        cdef uint8_t *extradata = <uint8_t *> av_malloc(self.video_packet.size * sizeof(uint8_t))
        memcpy(extradata, self.video_packet.data, self.video_packet.size)
        self.container.streams[0].codecpar.extradata = extradata
        self.container.streams[0].codecpar.extradata_size = self.video_packet.size
        av_packet_free(&self.video_packet)
        return True

    def write_audio_header(self, uint64_t pts, int length, object data):
        self.audio_packet = av_packet_alloc()
        self.init_packet(False, pts, length, data)
        cdef uint8_t *extradata = <uint8_t *> av_malloc(self.audio_packet.size * sizeof(uint8_t))
        memcpy(extradata, self.audio_packet.data, self.audio_packet.size)
        self.container.streams[1].codecpar.extradata = extradata
        self.container.streams[1].codecpar.extradata_size = self.audio_packet.size
        av_packet_free(&self.audio_packet)
        return True

    def write_header(self):
        return (avformat_write_header(self.container, NULL) >= 0)

    def write_video_packet(self, uint64_t pts, int length, object data):
        self.video_packet = av_packet_alloc()
        self.init_packet(True, pts, length, data)
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
                    return False
                av_packet_free(&self.previous_video_packet)
            self.previous_video_packet = self.video_packet
            self.video_packet = NULL
            return True

    def write_audio_packet(self, uint64_t pts, int length, object data):
        self.audio_packet = av_packet_alloc()
        self.init_packet(False, pts, length, data)
        if self.pts_origin == AV_NOPTS_VALUE:
            self.pts_origin = self.audio_packet.pts
        self.audio_packet.stream_index = 1
        self.audio_packet.pts -= self.pts_origin
        self.audio_packet.dts = self.audio_packet.pts
        av_packet_rescale_ts(self.audio_packet, RECORD_TIME_BASE, self.container.streams[1].time_base)
        if av_interleaved_write_frame(self.container, self.audio_packet)<0:
            return False
        av_packet_free(&self.video_packet)
        return True

    def close_container(self):
        cdef int duration
        if self.previous_video_packet:
            self.previous_video_packet.duration = 100000
            av_packet_rescale_ts(self.previous_video_packet, RECORD_TIME_BASE, self.container.streams[0].time_base)
            av_interleaved_write_frame(self.container, self.previous_video_packet)
            av_packet_free(&self.previous_video_packet)
        self.finish_time = <long> time(NULL)
        if av_write_trailer(self.container) <0:
            duration = 0
        else:
            duration = <int> ((self.pts_last - self.pts_origin)/1000000)
        avio_close(self.container.pb)
        avformat_free_context(self.container)
        self.has_finish = True
        return duration
        
    def __dealloc__(self):
        # 1. free codec
        # This also calls avcodec_close() internally
        if self.video_codec_ctx!=NULL:
            avcodec_free_context(&self.video_codec_ctx)
        if self.audio_codec_ctx!=NULL:
           avcodec_free_context(&self.audio_codec_ctx) 
        # 2.free packet
        if(self.previous_video_packet != NULL):
            av_packet_free(&self.previous_video_packet)
        if(self.video_packet != NULL):
            av_packet_free(&self.video_packet)
        if(self.audio_packet != NULL):
            av_packet_free(&self.audio_packet)
        # 3.free merger
        self.packet_merger_destroy()
        # 4.free container
        if self.has_finish == False:
            avio_close(self.container.pb)
            avformat_free_context(self.container)
