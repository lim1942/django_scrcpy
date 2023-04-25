import json

from django import forms
from general.models import Mobile


class MobileForm(forms.ModelForm):
    LOG_LEVEL_CHOICE = (
        ('verbose', 'verbose'),
        ('debug', 'debug'),
        ('info', 'info'),
        ('warn', 'warn'),
        ('error', 'error'),
    )
    VIDEO_ENCODER_CHOICE = (
        ('OMX.google.h264.encoder', 'OMX.google.h264.encoder'),
        ('OMX.qcom.video.encoder.avc', 'OMX.qcom.video.encoder.avc'),
        ('c2.android.avc.encoder', 'c2.android.avc.encoder'),
        ('OMX.qcom.video.encoder.hevc', 'OMX.qcom.video.encoder.hevc'),
        ('OMX.qcom.video.encoder.hevc.cq', 'OMX.qcom.video.encoder.hevc.cq'),
        ('c2.android.hevc.encoder', 'c2.android.hevc.encoder'),
    )
    AUDIO_ENCODER_CHOICE = (
        ('c2.android.opus.encoder', 'c2.android.opus.encoder'),
        ('c2.android.aac.encoder', 'c2.android.aac.encoder'),
        ('OMX.google.aac.encoder', 'OMX.google.aac.encoder'),
    )

    log_level = forms.ChoiceField(label='日志等级', help_text='scrcpy 服务的日志等级', choices=LOG_LEVEL_CHOICE, required=False)
    audio = forms.BooleanField(label="开启声音", help_text="需要提前解锁手机", required=False)
    max_size = forms.IntegerField(label='最大尺寸', help_text='720, 此时输出视频最大尺寸为720', required=False)
    video_bit_rate = forms.IntegerField(label='视频比特率', help_text='800000, 此时视频比特率为800kbs', required=False)
    audio_bit_rate = forms.IntegerField(label='音频比特率', help_text='128000, 此时音频比特率为128kbs', required=False)
    max_fps = forms.IntegerField(label='视频帧率', help_text='25, 此时最大帧率为25', required=False)
    lock_video_orientation = forms.IntegerField(label='锁定方向', help_text='-1不锁定屏幕，0为正，1，2，3为屏幕依次顺时针90°', required=False)
    crop = forms.CharField(label='裁剪尺寸', help_text="1224:1440:0:0，以(0,0)为原点的1224x1440屏幕区域", required=False)
    control = forms.BooleanField(label="远程操控", help_text="可远程控制手机", required=False)
    show_touches = forms.BooleanField(label="显示点击", help_text="显示屏幕点击操作", required=False)
    stay_awake = forms.BooleanField(label="保持唤醒", help_text="scrcpy连接时间设备屏幕常亮", required=False)
    video_codec_options = forms.CharField(label='视频编码参数', required=False)
    audio_codec_options = forms.CharField(label='音频编码参数', required=False)
    video_encoder = forms.ChoiceField(label='视频编码方式', choices=VIDEO_ENCODER_CHOICE, required=False)
    audio_encoder = forms.ChoiceField(label='音频编码方式', choices=AUDIO_ENCODER_CHOICE, required=False)
    power_off_on_close = forms.BooleanField(label='结束熄屏', required=False, help_text='scrcpy结束运行，屏幕熄灭')
    downsize_on_error = forms.BooleanField(label='尺寸适配', required=False, help_text='录屏编码错误，降低录屏尺寸适配')
    power_on = forms.BooleanField(label='开始亮屏', required=False, help_text='scrcpy开始运行，屏幕亮起')
    send_frame_meta = forms.BooleanField(label='帧元数据', required=False, help_text='发送帧元数据，视频延迟更低')

    def get_initial_for_field(self, field, field_name):
        """
        Return initial data for field on form. Use initial data from the form
        or the field, in that order. Evaluate callable values.
        """
        value = self.initial.get(field_name, field.initial)
        if callable(value):
            value = value()
        config_dict = json.loads(self.instance.config)
        if field_name in config_dict:
            return config_dict[field_name]
        else:
            return value

    def clean(self):
        self._validate_unique = True
        config_dict = json.loads(self.cleaned_data['config'])
        for field in self.cleaned_data:
            if field in config_dict:
                config_dict[field] = self.cleaned_data[field]
        self.cleaned_data['config'] = json.dumps(config_dict)
        return self.cleaned_data

    class Meta:
        model = Mobile
        fields = '__all__'
