#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <stdbool.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/time.h>


// 定义帧的pts
#define SC_PACKET_FLAG_CONFIG    (UINT64_C(1) << 63)
#define SC_PACKET_FLAG_KEY_FRAME (UINT64_C(1) << 62)
#define SC_PACKET_PTS_MASK (SC_PACKET_FLAG_KEY_FRAME - 1)
static const AVRational SCRCPY_TIME_BASE = {1, 1000000};


// 获取视频音频codec_id
static enum AVCodecID
sc_demuxer_to_avcodec_id(uint32_t codec_id) {
#define SC_CODEC_ID_H264 UINT32_C(0x68323634) // "h264" in ASCII
#define SC_CODEC_ID_H265 UINT32_C(0x68323635) // "h265" in ASCII
#define SC_CODEC_ID_AV1 UINT32_C(0x00617631) // "av1" in ASCII
#define SC_CODEC_ID_OPUS UINT32_C(0x6f707573) // "opus" in ASCII
#define SC_CODEC_ID_AAC UINT32_C(0x00616163) // "aac in ASCII"
#define SC_CODEC_ID_RAW UINT32_C(0x00726177) // "raw" in ASCII
    switch (codec_id) {
        case SC_CODEC_ID_H264:
            return AV_CODEC_ID_H264;
        case SC_CODEC_ID_H265:
            return AV_CODEC_ID_HEVC;
        case SC_CODEC_ID_AV1:
            return AV_CODEC_ID_AV1;
        case SC_CODEC_ID_OPUS:
            return AV_CODEC_ID_OPUS;
        case SC_CODEC_ID_AAC:
            return AV_CODEC_ID_AAC;
        case SC_CODEC_ID_RAW:
            return AV_CODEC_ID_PCM_S16LE;
        default:
            printf("Unknown codec id 0x%08" PRIx32, codec_id);
            return AV_CODEC_ID_NONE;
    }
}


// 创建socket用于接受需要录屏的流
int create_socket(const char *session_id)
{
	int sockfd = socket(AF_INET, SOCK_STREAM, 0);
	struct sockaddr_in serv_addr;
	serv_addr.sin_family = AF_INET;
	serv_addr.sin_addr.s_addr =  inet_addr("192.168.1.4");
	serv_addr.sin_port = htons(8888);
    if(connect(sockfd, (struct sockaddr *)(&serv_addr), sizeof(struct sockaddr)) == -1){
        fprintf(stderr, "socket Connect failed\n");
    }
    send(sockfd, session_id, strlen(session_id), 0);
	return sockfd;
}


// 是否包含字符
bool sc_str_list_contains(const char *list, char sep, const char *s) {
    char *p;
    do {
        p = strchr(list, sep);
        size_t token_len = p ? (size_t) (p - list) : strlen(list);
        if (!strncmp(list, s, token_len)) {
            return true;
        }
        if (p) {
            list = p + 1;
        }
    } while (p);
    return false;
}


// 创建封装容器
static const AVOutputFormat *
find_muxer(const char *name) {
    const AVOutputFormat *oformat = NULL;
    do {
        oformat = av_oformat_next(oformat);
    } while (oformat && !sc_str_list_contains(oformat->name, ',', name));
    return oformat;
}

// 视频编码codec
AVCodecContext * create_video_codec_ctx(enum AVCodecID codec_id, uint32_t width, uint32_t height){
    const AVCodec *codec = avcodec_find_decoder(codec_id);
    AVCodecContext *codec_ctx = avcodec_alloc_context3(codec);
    codec_ctx->flags |= AV_CODEC_FLAG_LOW_DELAY;
    codec_ctx->width = width;
    codec_ctx->height = height;
    codec_ctx->pix_fmt = AV_PIX_FMT_YUV420P;
    if (avcodec_open2(codec_ctx, codec, NULL) < 0) {
        printf("Demuxer : could not open video codec");
    }
    return codec_ctx;
}

// 音频编码codec
AVCodecContext * create_audio_codec_ctx(enum AVCodecID codec_id){
    const AVCodec *codec = avcodec_find_decoder(codec_id);
    AVCodecContext *codec_ctx = avcodec_alloc_context3(codec);
    codec_ctx->flags |= AV_CODEC_FLAG_LOW_DELAY;
    codec_ctx->channel_layout = AV_CH_LAYOUT_STEREO;
    codec_ctx->channels = 2;
    codec_ctx->sample_rate = 48000;
    if (avcodec_open2(codec_ctx, codec, NULL) < 0) {
        printf("Demuxer : could not open audio codec");
    }
    return codec_ctx;
}


int32_t
sc_read32be(const uint8_t *buf) {
    return ((uint32_t) buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3];
}


uint64_t
sc_read64be(const uint8_t *buf) {
    uint32_t msb = sc_read32be(buf);
    uint32_t lsb = sc_read32be(&buf[4]);
    return ((uint64_t) msb << 32) | lsb;
}


uint16_t
sc_read16be(const uint8_t *buf) {
    return (buf[0] << 8) | buf[1];
}

struct sc_packet_merger {
    uint8_t *config;
    size_t config_size;
};

void
sc_packet_merger_init(struct sc_packet_merger *merger) {
    merger->config = NULL;
}

void
sc_packet_merger_destroy(struct sc_packet_merger *merger) {
    free(merger->config);
}

bool
sc_packet_merger_merge(struct sc_packet_merger *merger, AVPacket *packet) {
    bool is_config = packet->pts == AV_NOPTS_VALUE;
    if (is_config) {
        free(merger->config);
        merger->config = malloc(packet->size);
        if (!merger->config) {
            printf("malloc error\n");
        }
        memcpy(merger->config, packet->data, packet->size);
        merger->config_size = packet->size;
    } else if (merger->config) {
        size_t config_size = merger->config_size;
        size_t media_size = packet->size;
        if (av_grow_packet(packet, config_size)) {
            printf("av_grow_packet error\n");
        }
        memmove(packet->data + config_size, packet->data, media_size);
        memcpy(packet->data, merger->config, config_size);
        free(merger->config);
        merger->config = NULL;
        // merger->size is meaningless when merger->config is NULL
    }
    return true;
}


bool main(int argc, char **argv){
    // 1.创建socket
    char *session_id  = argv[1];
    int sockfd = create_socket(session_id);

    // 2.创建封装容器
    av_register_all();
    const AVOutputFormat *format = find_muxer("mp4");
    AVFormatContext *format_ctx = avformat_alloc_context();
    format_ctx->oformat = (AVOutputFormat *) format;

    // 3.创建存储文件，写入metadata
    const char *filename = strncat(session_id,".mp4",4);
    printf("record to %s !!! \n", filename);
    avio_open(&format_ctx->pb, filename, AVIO_FLAG_WRITE);
    av_dict_set(&format_ctx->metadata, "comment","Recorded by django_scrcpy", 0);


    // 4.video_stream
    char meta_buf[4];
    recv(sockfd, meta_buf, 4, MSG_WAITALL);
    enum AVCodecID video_codec_id = sc_demuxer_to_avcodec_id(sc_read32be(meta_buf));
    uint32_t width;
    uint32_t height;
    recv(sockfd, meta_buf, 4, MSG_WAITALL);
    width = sc_read32be(meta_buf);
    recv(sockfd, meta_buf, 4, MSG_WAITALL);
    height = sc_read32be(meta_buf);
    AVCodecContext * video_codec_ctx = create_video_codec_ctx(video_codec_id, width, height);
    AVStream *video_stream = avformat_new_stream(format_ctx, video_codec_ctx->codec);
    avcodec_parameters_from_context(video_stream->codecpar, video_codec_ctx);

    // 5.audio_stream
    recv(sockfd, meta_buf, 4, MSG_WAITALL);
    enum AVCodecID audio_codec_id = sc_demuxer_to_avcodec_id(sc_read32be(meta_buf));
    if (audio_codec_id != AV_CODEC_ID_NONE){
        // AVCodecContext * audio_codec_ctx = create_audio_codec_ctx(audio_codec_id);
        // AVStream *audio_stream = avformat_new_stream(format_ctx, audio_codec_ctx->codec);
        // avcodec_parameters_from_context(audio_stream->codecpar, audio_codec_ctx);
    }

    // 6.read packet
    int64_t pts_origin = AV_NOPTS_VALUE;
    AVPacket *video_pkt_previous = NULL;
    AVPacket *packet = av_packet_alloc();
    struct sc_packet_merger merger;
    sc_packet_merger_init(&merger);
    for (;;) {
        // 6.1 read header
        uint8_t header[12];
        ssize_t r = recv(sockfd, header, 12, MSG_WAITALL);
        if (r<12){
            break;
        }
        uint64_t pts_flags = sc_read64be(header);
        uint32_t len = sc_read32be(&header[8]);

        // 6.2 read packet
        av_new_packet(packet, len);
        r = recv(sockfd, packet->data, len, MSG_WAITALL);
        if (r<len){
            break;
        }
        if (pts_flags & SC_PACKET_FLAG_CONFIG) {
            packet->pts = AV_NOPTS_VALUE;

        } else {
            packet->pts = pts_flags & SC_PACKET_PTS_MASK;
        }
        if (pts_flags & SC_PACKET_FLAG_KEY_FRAME) {
            packet->flags |= AV_PKT_FLAG_KEY;
        }
        packet->dts = packet->pts;
        sc_packet_merger_merge(&merger, packet);

        // 6.3 write header
        if (packet->pts == AV_NOPTS_VALUE){
            uint8_t *extradata = av_malloc(packet->size * sizeof(uint8_t));
            memcpy(extradata, packet->data, packet->size);
            format_ctx->streams[0]->codecpar->extradata = extradata;
            format_ctx->streams[0]->codecpar->extradata_size = packet->size;
            bool ok = (avformat_write_header(format_ctx, NULL) >= 0);
            if (!ok) {
                printf("Failed to write header to %s\n", filename);
            }
        }
        // 6.4 write packet
        else{
            printf("pts: %ld, packet size %d \n", packet->pts, packet->size);

            if (pts_origin == AV_NOPTS_VALUE) {
                pts_origin = packet->pts;
            }
            packet->pts -= pts_origin;
            packet->dts = packet->pts;
            if (video_pkt_previous) {
                // we now know the duration of the previous packet
                video_pkt_previous->duration = packet->pts- video_pkt_previous->pts;
                av_packet_rescale_ts(video_pkt_previous, SCRCPY_TIME_BASE, format_ctx->streams[0]->time_base);
                printf("packet size %d\n", video_pkt_previous->size);
                bool ok = av_interleaved_write_frame(format_ctx, video_pkt_previous)>=0;
                if (!ok){
                    printf("Failed to write packet to %s\n", filename);
                }
                av_packet_free(&video_pkt_previous);

            }
            video_pkt_previous = av_packet_clone(packet);
        }
        av_packet_unref(packet);
    }
    if (video_pkt_previous){
        video_pkt_previous->duration = 100000;
        av_packet_rescale_ts(video_pkt_previous, SCRCPY_TIME_BASE, format_ctx->streams[0]->time_base);
        av_interleaved_write_frame(format_ctx, video_pkt_previous)>=0;
    }
    int ret = av_write_trailer(format_ctx);
    if (ret < 0) {
        printf("Failed to write trailer to %s", filename);
    }
    avio_close(format_ctx->pb);
    avformat_free_context(format_ctx);
    printf("success!!\n");
    return true;
}