import json

from django.contrib.auth.models import User
from django.db import models


LOG_LEVEL_CHOICE = (
    ('verbose', 'verbose'),
    ('debug', 'debug'),
    ('info', 'info'),
    ('warn', 'warn'),
    ('error', 'error'),
)

VIDEO_CODEC_CHOICE = (
    ('h264', 'h264'),
    ('h265', 'h265'),
)

AUDIO_CODEC_CHOICE = (
    ('aac', 'aac'),
    ('opus', 'opus'),
    ('raw', 'raw'),
)

VIDEO_ENCODER_CHOICE = (
    # 264
    ('OMX.google.h264.encoder', 'OMX.google.h264.encoder'),
    ('OMX.qcom.video.encoder.avc', 'OMX.qcom.video.encoder.avc'),
    ('c2.android.avc.encoder', 'c2.android.avc.encoder'),
    ('c2.mtk.avc.encoder', 'c2.mtk.avc.encoder'),
    ('OMX.MTK.VIDEO.ENCODER.AVC', 'OMX.MTK.VIDEO.ENCODER.AVC'),
    # 265
    ('OMX.qcom.video.encoder.hevc', 'OMX.qcom.video.encoder.hevc'),
    ('OMX.qcom.video.encoder.hevc.cq', 'OMX.qcom.video.encoder.hevc.cq'),
    ('c2.android.hevc.encoder', 'c2.android.hevc.encoder'),
    ('c2.mtk.hevc.encoder', 'c2.mtk.hevc.encoder'),
    ('OMX.MTK.VIDEO.ENCODER.HEVC', 'OMX.MTK.VIDEO.ENCODER.HEVC')
)

AUDIO_ENCODER_CHOICE = (
    # opus
    ('c2.android.opus.encoder', 'c2.android.opus.encoder'),
    # acc
    ('c2.android.aac.encoder', 'c2.android.aac.encoder'),
    ('OMX.google.aac.encoder', 'OMX.google.aac.encoder'),
    # raw
    ('', ''),
)

AUDIO_SOURCE_CHOICE = (
    # 默认
    ('output', 'output'),
    # 耳机
    ('mic', 'mic'),
)

RECORDER_FORMAT = (
    ('mp4', 'mp4'),
    ('mkv', 'mkv')
)

DEFAULT_SCRCPY_KWARGS = {
    "recorder_enable": False,
    "recorder_format": "mp4",
    # 1 scrcpy adb-socket-id, 用于手机区分多个启动的scrcpy。每次运行自动生成
    # "scid": -1,
    # 2. scrcpy日志等级
    # "log_level": "verbose",
    # 3 是否开启画面
    # "video": True,
    # 4 是否开启声音
    "audio": True,
    # 5 音频编码类型
    "video_codec": "h264",
    # 6 音频编码类型
    "audio_codec": "aac",
    # 7.声音来源
    "audio_source": "output",
    # 8 画面最大尺寸
    "max_size": 720,
    # 9 视频比特率
    "video_bit_rate": 800000,
    # 10 音频比特率
    "audio_bit_rate": 128000,
    # 11 视频帧率
    "max_fps": 25,
    # 12 -1是不锁定屏幕旋转
    # "lock_video_orientation": -1,
    # 13 通过tunnel_forward方式创建adb-socket
    "tunnel_forward": True,
    # 14 画面裁剪
    "crop": "",
    # 15 开启控制
    "control": True,
    # 16 录制画面id，默认是0
    # "display_id": 0,
    # 17 显示屏幕点击
    "show_touches": False,
    # 18 保持设备唤醒
    "stay_awake": True,
    # 19 视频编码参数，次参数为视频OMX.google.h264.encoder在有些机型报错
    "video_codec_options": "profile=1,level=2",
    # 20 音频编码参数
    "audio_codec_options": "",
    # 21 视频具体编码
    "video_encoder": "",
    # 22 音频具体编码
    "audio_encoder": "",
    # 23 scrcpy解锁设备锁屏
    "power_off_on_close": False,
    # 24 clipboard_autosync为True，在有选择文本才同步剪切板，False为随时获取剪切板
    "clipboard_autosync": False,
    # 25 录屏编码错误，降低录屏尺寸适配
    # "downsize_on_error": True,
    # 26 开启清理线程
    # "cleanup": True,
    # 27 启动亮屏
    "power_on": True,
    # 28 列出支持的编码，为True时列出，此时server不运行
    # "list_encoders": False,
    # 29 列出display_id,为True时列出，此时server不运行
    # "list_displays": False,
    # 30 发送设备源信息，设备名，分辨率等
    # "send_device_meta": True,
    # 31 发送帧源信息
    # "send_frame_meta": True,
    # 32 发送video socket连接成功dummy_byte
    # "send_dummy_byte": True,
    # 33 发送编码源信息
    # "send_codec_meta": True,
    # 34 仅发送裸流，此时send_device_meta，send_frame_meta，send_dummy_byte，send_codec_meta会被置为False
    # "raw_stream": False
}


class Mobile(models.Model):
    user = models.ForeignKey(User, verbose_name='所属用户', on_delete=models.CASCADE, default=None, null=True, blank=True)
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
        ordering = ('-updated_time', )


class Video(models.Model):
    video_id = models.CharField("video_id", max_length=127, unique=True, null=False, blank=False, db_index=True)
    device_id = models.CharField("device_id", max_length=127, null=False, blank=False, db_index=True)
    format = models.CharField('文件格式', max_length=32, null=False, blank=False, db_index=True)
    duration = models.IntegerField("视频时长(秒)", null=False, blank=False)
    size = models.IntegerField('视频大小(KB)', null=False, blank=False)
    start_time = models.DateTimeField("开始时间", db_index=True)
    finish_time = models.DateTimeField("结束时间", db_index=True)
    config = models.TextField("配置详情", default=json.dumps(DEFAULT_SCRCPY_KWARGS), help_text='配置视频分辨率，帧率等')
    updated_time = models.DateTimeField("更新时间", auto_now=True, db_index=True)
    name = models.CharField('名称', max_length=32, blank=True, null=False)
    details = models.TextField("备注信息", blank=True)

    def __str__(self):
        return self.video_id
    
    class Meta:
        verbose_name_plural = verbose_name = '录屏'
        ordering = ('-finish_time',)


class Picture(models.Model):
    device_id = models.CharField("device_id", max_length=127, null=False, blank=False, db_index=True)
    picture = models.ImageField("截图", upload_to='picture')
    name = models.CharField('名称', max_length=32, blank=True, null=False)
    details = models.TextField("备注信息", blank=True)
    updated_time = models.DateTimeField("更新时间", auto_now=True, db_index=True)
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    def __str__(self):
        return self.device_id
    
    class Meta:
        verbose_name_plural = verbose_name = '截图'
        ordering = ('-created_time',)
