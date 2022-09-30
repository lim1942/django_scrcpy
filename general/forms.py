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
    ENCODER_NAME_CHOICE = (
        ('OMX.google.h264.encoder', 'OMX.google.h264.encoder'),
        ('OMX.qcom.video.encoder.avc', 'OMX.qcom.video.encoder.avc'),
        ('c2.qti.avc.encoder', 'c2.qti.avc.encoder'),
        ('c2.android.avc.encoder', 'c2.android.avc.encoder'),
    )
    log_level = forms.ChoiceField(label='日志等级', choices=LOG_LEVEL_CHOICE, required=False, help_text='scrcpy 服务的日志等级')
    max_size = forms.IntegerField(label='最大尺寸', help_text='720, 此时输出视频最大尺寸为720', required=False)
    bit_rate = forms.IntegerField(label='比特率', help_text='800000, 此时比特率为800kbs', required=False)
    max_fps = forms.IntegerField(label='视频帧率', help_text='25, 此时最大帧率为25', required=False)
    lock_video_orientation = forms.IntegerField(label='锁定方向', help_text='-1不锁定屏幕，0为正，1，2，3为屏幕依次顺时针90°', required=False)
    crop = forms.CharField(label='裁剪尺寸', help_text="1224:1440:0:0，以(0,0)为原点的1224x1440屏幕区域", required=False)
    control = forms.BooleanField(label="远程操控", help_text="可远程控制手机", required=False)
    display_id = forms.IntegerField(label="录屏id", help_text="scrcpy_server的录屏id", required=False)
    show_touches = forms.BooleanField(label="显示点击", help_text="显示屏幕点击操作", required=False)
    stay_awake = forms.BooleanField(label="保持唤醒", help_text="scrcpy连接时间设备屏幕常亮", required=False)
    codec_options = forms.CharField(label='编码参数', required=False)
    encoder_name = forms.ChoiceField(label='编码方式', choices=ENCODER_NAME_CHOICE, required=False)
    power_off_on_close = forms.BooleanField(label='结束熄屏', required=False, help_text='scrcpy结束运行，屏幕熄灭')
    downsize_on_error = forms.BooleanField(label='尺寸适配', required=False, help_text='录屏编码错误，降低录屏尺寸适配')
    power_on = forms.BooleanField(label='开始亮屏', required=False, help_text='scrcpy开始运行，屏幕亮起')
    send_frame_meta = forms.BooleanField(label='帧元数据', required=False, help_text='发送帧元数据，视频延迟更低')
    connect_timeout = forms.IntegerField(label='超时时间', required=False, help_text='连接scrcpy超时时间，300=3s')
    deploy_shell_log = forms.BooleanField(label='部署日志', required=False, help_text='是否打开scrcpy的部署日志')

    def get_initial_for_field(self, field, field_name):
        """
        Return initial data for field on form. Use initial data from the form
        or the field, in that order. Evaluate callable values.
        """
        value = self.initial.get(field_name, field.initial)
        if callable(value):
            value = value()
        config_dict = json.loads(self.instance.config)
        if field_name == 'log_level':
            return config_dict.get(field_name, 'verbose')
        if field_name == 'max_size':
            return config_dict.get(field_name, 720)
        elif field_name == 'bit_rate':
            return config_dict.get(field_name, 800000)
        elif field_name == 'max_fps':
            return config_dict.get(field_name, 25)
        elif field_name == 'lock_video_orientation':
            return config_dict.get(field_name, -1)
        elif field_name == 'crop':
            return config_dict.get(field_name, '')
        elif field_name == 'control':
            return config_dict.get(field_name, True)
        elif field_name == 'display_id':
            return config_dict.get(field_name, 0)
        elif field_name == 'show_touches':
            return config_dict.get(field_name, False)
        elif field_name == 'stay_awake':
            return config_dict.get(field_name, True)
        elif field_name == 'codec_options':
            return config_dict.get(field_name, "profile=1,level=2")
        elif field_name == 'encoder_name':
            return config_dict.get(field_name, 'OMX.google.h264.encoder')
        elif field_name == 'power_off_on_close':
            return config_dict.get(field_name, False)
        elif field_name == 'downsize_on_error':
            return config_dict.get(field_name, True)
        elif field_name == 'power_on':
            return config_dict.get(field_name, True)
        elif field_name == 'send_frame_meta':
            return config_dict.get(field_name, True)
        elif field_name == 'connect_timeout':
            return config_dict.get(field_name, 300)
        elif field_name == 'deploy_shell_log':
            return config_dict.get(field_name, True)
        else:
            return value

    def clean(self):
        self._validate_unique = True
        new_config_dict = dict()
        for field in ('log_level', 'max_size', 'bit_rate', 'max_fps', 'lock_video_orientation', 'crop', 'control',
                      'display_id', 'show_touches', 'stay_awake', 'codec_options', 'encoder_name', 'power_off_on_close',
                      'downsize_on_error', 'power_on', 'send_frame_meta', 'connect_timeout', 'deploy_shell_log'):
            new_config_dict[field] = self.cleaned_data[field]
        self.cleaned_data['config'] = json.dumps(new_config_dict)
        return self.cleaned_data

    class Meta:
        model = Mobile
        fields = '__all__'
