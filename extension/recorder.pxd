from libc.stdint cimport int64_t, uint64_t, uint32_t, uint8_t, UINT_LEAST32_MAX
from libc.string cimport memcpy, memmove
from libc.stdlib cimport malloc, free
from libc.time cimport time


cdef extern from "libavutil/avutil.h" nogil:
    cdef int64_t AV_NOPTS_VALUE

    ctypedef struct AVDictionary:
        pass

    cdef struct AVRational:
        int num
        int den

    cdef void* av_malloc(size_t size)

    cdef int av_dict_set(AVDictionary **pm, const char *key, const char *value, int flags)


cdef extern from "libavformat/avformat.h" nogil:
    cdef int LIBAVFORMAT_VERSION_INT
    cdef int AV_VERSION_INT(int a, int b, int c)
    cdef int AVIO_FLAG_WRITE
    cdef int AV_PKT_FLAG_KEY

    ctypedef struct AVIOContext:
        pass

    cdef struct AVCodecParameters:
        uint8_t *extradata
        int extradata_size
        
    cdef struct AVStream:
        AVCodecParameters *codecpar
        AVRational time_base

    cdef struct AVOutputFormat:
        const char *name

    cdef struct AVFormatContext:
        AVOutputFormat *oformat
        AVIOContext *pb
        AVDictionary *metadata
        AVStream **streams
        int64_t duration

    cdef void av_register_all()

    cdef AVFormatContext* avformat_alloc_context()

    cdef const AVOutputFormat* av_muxer_iterate(void **opaque)

    cdef const AVOutputFormat* av_oformat_next(AVOutputFormat *oformat)

    cdef int avio_open(AVIOContext **s, char *url, int flags)

    cdef AVStream* avformat_new_stream( AVFormatContext *ctx, AVCodec *c)

    cdef int avformat_write_header(AVFormatContext *ctx, AVDictionary **options)

    int av_interleaved_write_frame(AVFormatContext *s, AVPacket *pkt)

    cdef int av_write_trailer(AVFormatContext *ctx)

    cdef int avio_close(AVIOContext *s)

    cdef int avformat_free_context(AVFormatContext *ctx)


cdef extern from "libavcodec/avcodec.h" nogil:
    cdef int AV_CODEC_FLAG_LOW_DELAY
    cdef int AV_CH_LAYOUT_STEREO

    cdef enum AVCodecID:
        AV_CODEC_ID_H264
        AV_CODEC_ID_HEVC
        AV_CODEC_ID_H265
        AV_CODEC_ID_AV1
        AV_CODEC_ID_OPUS
        AV_CODEC_ID_AAC
        AV_CODEC_ID_PCM_S16LE
        AV_CODEC_ID_NONE

    cdef enum AVPixelFormat:
        AV_PIX_FMT_YUV420P

    ctypedef struct AVCodec:
        pass

    ctypedef struct AVCodecParameters:
        pass

    cdef struct AVCodecContext:
        int flags
        int width
        int height
        AVCodec *codec
        AVPixelFormat pix_fmt
        int sample_rate
        int channels
        int channel_layout

    cdef struct AVPacket:
        int64_t pts
        int64_t dts
        uint8_t *data
        int size
        int stream_index
        int flags
        int duration
        int64_t pos

    cdef AVCodec* avcodec_find_decoder(AVCodecID id)

    cdef AVPacket* av_packet_alloc()

    cdef int av_new_packet(AVPacket*, int)

    cdef void av_packet_unref(AVPacket *pkt)

    cdef AVCodecContext* avcodec_alloc_context3(AVCodec *codec)
    
    cdef int avcodec_open2(AVCodecContext *ctx, AVCodec *codec, AVDictionary **options)

    cdef int avcodec_parameters_from_context(AVCodecParameters *par, const AVCodecContext *codec)

    cdef int av_grow_packet(AVPacket *pkt, int grow_by)

    cdef AVPacket *av_packet_clone(const AVPacket *src)

    cdef void av_packet_free(AVPacket **pkt)

    cdef void avcodec_free_context(AVCodecContext **avctx)

    cdef void av_packet_rescale_ts(AVPacket *pkt, AVRational src_tb, AVRational dst_tb)


cdef const AVOutputFormat* find_muxer(const char *name)


cdef struct video_packet_merger:
    uint8_t *config
    size_t config_size
    

cdef class Recorder(object):
    cdef bint has_audio
    cdef int64_t pts_origin
    cdef int64_t pts_last
    cdef long start_time
    cdef long finish_time
    cdef AVPacket *previous_video_packet
    cdef AVPacket *video_packet
    cdef AVPacket *audio_packet
    cdef AVFormatContext *container
    cdef AVCodecContext *video_codec_ctx
    cdef AVCodecContext *audio_codec_ctx
    cdef video_packet_merger merger

    cdef uint32_t read32be(self, const uint8_t *data)

    cdef uint64_t read64be(self, const uint8_t *data)

    cdef void init_packet(self, AVPacket * packet, const uint8_t *pts, int length, const uint8_t *data)

    cdef void packet_merger_init(self)

    cdef void packet_merger_merge(self, AVPacket *packet)

    cdef void packet_merger_destroy(self)

    cdef AVCodecID get_avcodec_id(self, const uint8_t *codec_name)

    cpdef bint add_video_stream(self, const uint8_t *codec_name, const uint8_t *width, const uint8_t *height) except False

    cpdef bint add_audio_stream(self, const uint8_t *codec_name) except False

    cpdef bint write_video_header(self, const uint8_t *pts, int length, const uint8_t *data) except False

    cpdef bint write_audio_header(self, const uint8_t *pts, int length, const uint8_t *data) except False

    cpdef bint write_header(self) except False

    cpdef bint write_video_packet(self, const uint8_t *pts, int length, const uint8_t *data) except False

    cpdef bint write_audio_packet(self, const uint8_t *pts, int length, const uint8_t *data) except False

    cpdef int close_container(self) except 0
