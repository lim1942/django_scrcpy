#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <stdbool.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/time.h>


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


static const AVOutputFormat *
find_muxer(const char *name) {
    const AVOutputFormat *oformat = NULL;
    do {
        oformat = av_oformat_next(oformat);
    } while (oformat && !sc_str_list_contains(oformat->name, ',', name));
    return oformat;
}


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



bool main(int argc, char **argv){
    char *session_id  = argv[1];
    // 1.创建socket
    int sockfd = create_socket(session_id);
    // 2.创建封装容器
    const AVOutputFormat *format = find_muxer("mp4");
    AVFormatContext *format_ctx = avformat_alloc_context();
    format_ctx->oformat = (AVOutputFormat *) format;
    // 3.创建存储文件，写入metadata
    const char *filename = strncat(session_id,".mp4",4);
    printf("record to %s !!! \n", filename);
    avio_open(&format_ctx->pb, filename, AVIO_FLAG_WRITE);
    av_dict_set(&format_ctx->metadata, "comment","Recorded by django_scrcpy", 0);
    // 4.写入video_stream
    av_register_all();
    AVCodecContext * video_codec_ctx = create_video_codec_ctx(AV_CODEC_ID_H264, 328, 720);
    AVStream *video_stream = avformat_new_stream(format_ctx, video_codec_ctx->codec);
    avcodec_parameters_from_context(video_stream->codecpar, video_codec_ctx);
    // 5.写入audio_stream
    AVCodecContext * audio_codec_ctx = create_audio_codec_ctx(AV_CODEC_ID_OPUS);
    AVStream *audio_stream = avformat_new_stream(format_ctx, audio_codec_ctx->codec);
    avcodec_parameters_from_context(audio_stream->codecpar, audio_codec_ctx);

    printf("success!!\n");
    return true;
}