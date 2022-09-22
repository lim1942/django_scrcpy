import json

from django import forms
from general.models import Mobile


class MobileForm(forms.ModelForm):
    encoder_name_choice = (
        ('OMX.google.h264.encoder', 'OMX.google.h264.encoder'),
        ('OMX.qcom.video.encoder.avc', 'OMX.qcom.video.encoder.avc'),
        ('c2.qti.avc.encoder', 'c2.qti.avc.encoder'),
        ('c2.android.avc.encoder', 'c2.android.avc.encoder'),
    )
    max_size = forms.IntegerField(label='最大尺寸', help_text='720, 此时输出视频最大尺寸为720', required=False)
    bit_rate = forms.IntegerField(label='比特率', help_text='800, 此时比特率为800', required=False)
    max_fps = forms.IntegerField(label='视频帧率', help_text='25, 此时最大帧率为25', required=False)
    lock_video_orientation = forms.IntegerField(label='锁定方向', help_text='-1不锁定屏幕，0为正，1，2，3为屏幕依次顺时针90°', required=False)
    crop = forms.CharField(label='裁剪尺寸', help_text="1224:1440:0:0，以(0,0)为原点的1224x1440屏幕区域", required=False)
    stay_awake = forms.BooleanField(label="保持唤醒", help_text="scrcpy连接时间设备屏幕常亮", required=False)
    codec_options = forms.CharField(label='编码参数', required=False)
    encoder_name = forms.ChoiceField(label='编码方式', choices=encoder_name_choice, required=False)
    send_frame_meta = forms.BooleanField(label='帧元数据', required=False, help_text='发送帧元数据时，视频延迟更低')
    connect_timeout = forms.IntegerField(label='超时时间', required=False, help_text='连接scrcpy超时时间，300=3s')

    def get_initial_for_field(self, field, field_name):
        """
        Return initial data for field on form. Use initial data from the form
        or the field, in that order. Evaluate callable values.
        """
        value = self.initial.get(field_name, field.initial)
        if callable(value):
            value = value()
        config_dict = json.loads(self.instance.config)
        if field_name == 'max_size':
            return config_dict.get(field_name, 720)
        elif field_name == 'bit_rate':
            return config_dict.get(field_name, 800)
        elif field_name == 'max_fps':
            return config_dict.get(field_name, 25)
        elif field_name == 'lock_video_orientation':
            return config_dict.get(field_name, -1)
        elif field_name == 'crop':
            return config_dict.get(field_name, '')
        elif field_name == 'stay_awake':
            return config_dict.get(field_name, True)
        elif field_name == 'codec_options':
            return config_dict.get(field_name, '')
        elif field_name == 'encoder_name':
            return config_dict.get(field_name, 'OMX.google.h264.encoder')
        elif field_name == 'send_frame_meta':
            return config_dict.get(field_name, True)
        elif field_name == 'connect_timeout':
            return config_dict.get(field_name, 300)
        else:
            return value

    def clean(self):
        self._validate_unique = True
        new_config_dict = dict()
        for field in ('max_size', 'bit_rate', 'max_fps', 'lock_video_orientation', 'crop', 'stay_awake','codec_options',
                      'encoder_name', 'send_frame_meta', 'connect_timeout'):
            new_config_dict[field] = self.cleaned_data[field]
        self.cleaned_data['config'] = json.dumps(new_config_dict)
        print(self.cleaned_data)
        return self.cleaned_data

    class Meta:
        model = Mobile
        fields = '__all__'
