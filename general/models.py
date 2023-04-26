import json
from django.db import models

DEFAULT_SCRCPY_KWARGS = {
    # 1 scrcpy adb-socket-id, 用于手机区分多个启动的scrcpy。每次运行自动生成
    # "scid": -1,
    # 2. scrcpy日志等级
    "log_level": "verbose",
    # 3 是否开启声音
    "audio": True,
    # 4 音频编码类型
    "video_codec": "h264",
    # 5 音频编码类型
    "audio_codec": "opus",
    # 6 画面最大尺寸
    "max_size": 720,
    # 7 视频比特率
    "video_bit_rate": 8000000,
    # 8 音频比特率
    "audio_bit_rate": 128000,
    # 9 视频帧率
    "max_fps": 25,
    # 10 -1是不锁定屏幕旋转
    "lock_video_orientation": -1,
    # 11 通过tunnel_forward方式创建adb-socket
    "tunnel_forward": True,
    # 12 画面裁剪
    "crop": "",
    # 13 开启控制
    "control": True,
    # 14 录制画面id，默认是0
    # "display_id": 0,
    # 15 显示屏幕点击
    "show_touches": False,
    # 16 保持设备唤醒
    "stay_awake": True,
    # 17 视频编码参数，次参数为视频OMX.google.h264.encoder在有些机型报错
    "video_codec_options": "profile=1,level=2",
    # 18 音频编码参数
    "audio_codec_options": "",
    # 19 视频具体编码
    "video_encoder": "OMX.google.h264.encoder",
    # 20 音频具体编码
    "audio_encoder": "c2.android.opus.encoder",
    # 21 scrcpy解锁设备锁屏
    "power_off_on_close": False,
    # 22 clipboard_autosync为True，在有选择文本才同步剪切板，False为随时获取剪切板
    "clipboard_autosync": False,
    # 23 报错时降低录屏尺寸
    "downsize_on_error": True,
    # 24 开启清理线程
    "cleanup": True,
    # 25 启动亮屏
    "power_on": True,
    # 26 列出支持的编码，为True时列出，此时server不运行
    "list_encoders": False,
    # 27 列出display_id,为True时列出，此时server不运行
    "list_displays": False,
    # 28 发送设备源信息，设备名，分辨率等
    "send_device_meta": True,
    # 29 发送帧源信息
    "send_frame_meta": True,
    # 30 发送video socket连接成功dummy_byte
    "send_dummy_byte": True,
    # 31 发送编码源信息
    "send_codec_meta": True,
    # 32 仅发送裸流，此时send_device_meta，send_frame_meta，send_dummy_byte，send_codec_meta会被置为False
    "raw_video_stream": False
}


class Mobile(models.Model):
    device_id = models.CharField("device_id", max_length=127, unique=True, null=False, blank=False)
    device_name = models.CharField('设备名', max_length=32, blank=True, null=False)
    device_type = models.CharField('设备类型', max_length=32, blank=True, null=False)
    config = models.TextField("配置详情", default=json.dumps(DEFAULT_SCRCPY_KWARGS), help_text='配置视频分辨率，帧率等')
    details = models.TextField("备注信息", blank=True)
    updated_time = models.DateTimeField("更新时间", auto_now=True, db_index=True)
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    def __str__(self):
        return self.device_id

    class Meta:
        verbose_name_plural = verbose_name = '手机'
        ordering = ('updated_time', 'created_time')
