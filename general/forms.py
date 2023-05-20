import json

from django import forms
from general.models import Mobile, LOG_LEVEL_CHOICE, VIDEO_CODEC_CHOICE, AUDIO_CODEC_CHOICE


class MobileForm(forms.ModelForm):
    recorder = forms.BooleanField(label="开启录屏", help_text="需要linux部署", required=False)
    recorder_mkv = forms.BooleanField(label="mkv录屏", help_text="关闭时为mp4录屏", required=False)
    log_level = forms.ChoiceField(label='日志等级', help_text='scrcpy 服务的日志等级', choices=LOG_LEVEL_CHOICE, required=False)
    audio = forms.BooleanField(label="开启声音", help_text="需要提前解锁手机", required=False)
    video_codec = forms.ChoiceField(label='视频codec', choices=VIDEO_CODEC_CHOICE, required=False)
    audio_codec = forms.ChoiceField(label='音频codec', choices=AUDIO_CODEC_CHOICE, required=False)
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
    power_off_on_close = forms.BooleanField(label='结束熄屏', required=False, help_text='scrcpy结束运行，屏幕熄灭')
    downsize_on_error = forms.BooleanField(label='尺寸适配', required=False, help_text='录屏编码错误，降低录屏尺寸适配')
    power_on = forms.BooleanField(label='开始亮屏', required=False, help_text='scrcpy开始运行，屏幕亮起')

    def get_initial_for_field(self, field, field_name):
        """
        Return initial data for field on form. Use initial data from the form
        or the field, in that order. Evaluate callable values.
        """
        value = self.initial.get(field_name, field.initial)
        if callable(value):
            value = value()
        return json.loads(self.instance.config).get(field_name, value)

    def clean(self):
        self._validate_unique = True
        config_dict = json.loads(self.instance.config)
        # update config_dict by form fields
        config_dict.update({field: self.cleaned_data[field] for field in self.cleaned_data if field in config_dict})
        # valid mp4 video recorder
        if (config_dict['recorder']) and (not config_dict['recorder_mkv']) and (config_dict['audio_codec']!='aac'):
            raise forms.ValidationError("recording: mp4 audio_codec only support aac!!!")
        # restore config_dict to config str
        self.cleaned_data['config'] = json.dumps(config_dict)
        return self.cleaned_data

    class Meta:
        model = Mobile
        fields = '__all__'
