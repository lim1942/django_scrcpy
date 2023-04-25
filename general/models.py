import json
from django.db import models


DEFAULT_SCRCPY_KWARGS = {
                # "scid": -1,
                "log_level": "verbose",
                "audio": True,
                "video_codec": "h264",
                "audio_codec": "opus",
                "max_size": 720,
                "video_bit_rate": 8000000,
                "audio_bit_rate": 128000,
                "max_fps": 25,
                "lock_video_orientation": -1,
                "tunnel_forward": True,
                "crop": "",
                "control": True,
                # "display_id": 0,
                "show_touches": False,
                "stay_awake": True,
                "video_codec_options": "profile=1,level=2",
                "audio_codec_options": "",
                "video_encoder": "OMX.google.h264.encoder",
                "audio_encoder": "c2.android.opus.encoder",
                "power_off_on_close": False,
                "clipboard_autosync": True,
                "downsize_on_error": True,
                "cleanup": True,
                "power_on": True,
                "list_encoders": False,
                "list_displays": False,
                "send_device_meta": True,
                "send_frame_meta": True,
                "send_dummy_byte": True,
                "send_codec_meta": True,
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
