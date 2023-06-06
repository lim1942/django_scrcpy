cdef uint64_t SC_PACKET_FLAG_CONFIG = (1 << 63)
cdef uint64_t SC_PACKET_FLAG_KEY_FRAME = (1 << 62)
cdef uint64_t SC_PACKET_PTS_MASK = (SC_PACKET_FLAG_KEY_FRAME - 1)
cdef AVRational RECORD_TIME_BASE = {"num":1, "den":1000000}


cdef class Recorder(object):
    def __cinit__(self, const char *muxer_name, const char *filename, bint has_audio):
        # 1.mark finish
        self.has_finish = False
        # 2.has audio
        self.has_audio  = has_audio
        # 3.open a container
        self.container = avformat_alloc_context()
        cdef void *opaque = NULL
        while True:
            oformat = av_muxer_iterate(&opaque)
            assert oformat
            if muxer_name in oformat.name:
                self.container.oformat = <AVOutputFormat *>oformat
                break
        avio_open(&self.container.pb, filename, AVIO_FLAG_WRITE)
        av_dict_set(&self.container.metadata, "comment","Recorded by django_scrcpy", 0)
        # 4.time info
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
        cdef size_t config_size
        cdef size_t media_size
        if packet.pts == AV_NOPTS_VALUE:
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

    cdef AVPacket* init_packet(self,  uint64_t pts, int length, uint8_t* data):
        cdef AVPacket* packet = av_packet_alloc()
        # av_new_packet(packet, length)
        # memcpy(packet.data, data, packet.size)
        packet.data = data
        if (SC_PACKET_FLAG_CONFIG & pts):
            packet.pts = AV_NOPTS_VALUE
        else:
            packet.pts = pts & SC_PACKET_PTS_MASK
        if pts & SC_PACKET_FLAG_KEY_FRAME:
            packet.flags |=  AV_PKT_FLAG_KEY
        packet.dts = packet.pts
        return packet

    def write_video_header(self, uint64_t pts, int length, uint8_t* data):
        self.packet_merger_init()
        cdef AVPacket* packet = self.init_packet(pts, length, data)
        self.packet_merger_merge(packet)
        cdef uint8_t *extradata = <uint8_t *> av_malloc(packet.size * sizeof(uint8_t))
        memcpy(extradata, packet.data, packet.size)
        self.container.streams[0].codecpar.extradata = extradata
        self.container.streams[0].codecpar.extradata_size = packet.size
        av_packet_free(&packet)
        return True

    def write_audio_header(self, uint64_t pts, int length, uint8_t* data):
        cdef AVPacket* packet = self.init_packet(pts, length, data)
        cdef uint8_t *extradata = <uint8_t *> av_malloc(packet.size * sizeof(uint8_t))
        memcpy(extradata, packet.data, packet.size)
        self.container.streams[1].codecpar.extradata = extradata
        self.container.streams[1].codecpar.extradata_size = packet.size
        av_packet_free(&packet)
        return True

    def write_header(self):
        return (avformat_write_header(self.container, NULL) >= 0)

    def write_video_packet(self, uint64_t pts, int length, uint8_t* data):
        cdef AVPacket* packet = self.init_packet(pts, length, data)
        if self.pts_origin == AV_NOPTS_VALUE:
            self.pts_origin = packet.pts
        # config packet
        if packet.pts == AV_NOPTS_VALUE:
            self.packet_merger_merge(packet)
        # data packet
        else:
            self.pts_last = packet.pts
            packet.stream_index = 0
            packet.pts -= self.pts_origin
            packet.dts = packet.pts
            self.packet_merger_merge(packet)
            if self.previous_video_packet:
                self.previous_video_packet.duration = packet.pts- self.previous_video_packet.pts
                av_packet_rescale_ts(self.previous_video_packet, RECORD_TIME_BASE, self.container.streams[0].time_base)
                if av_interleaved_write_frame(self.container, self.previous_video_packet)<0:
                    return False
                av_packet_free(&self.previous_video_packet)
            self.previous_video_packet = packet
            packet = NULL
            return True

    def write_audio_packet(self, uint64_t pts, int length, uint8_t* data):
        cdef AVPacket* packet = self.init_packet(pts, length, data)
        if self.pts_origin == AV_NOPTS_VALUE:
            self.pts_origin = packet.pts
        packet.stream_index = 1
        packet.pts -= self.pts_origin
        packet.dts = packet.pts
        av_packet_rescale_ts(packet, RECORD_TIME_BASE, self.container.streams[1].time_base)
        if av_interleaved_write_frame(self.container, packet)<0:
            return False
        av_packet_free(&packet)
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
        # 3.free merger
        self.packet_merger_destroy()
        # 4.free container
        if self.has_finish == False:
            avio_close(self.container.pb)
            avformat_free_context(self.container)
