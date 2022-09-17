import json
from django import forms
from django.forms.widgets import Textarea
from general.models import Mobile


class MobileForm(forms.ModelForm):

    def clean_config(self):
        config = self.cleaned_data['config']
        try:
            config = config or '{}'
            assert isinstance(json.loads(config), dict)
        except Exception as e:
            raise forms.ValidationError("请提json配置")
        return config

    class Meta:
        model = Mobile
        fields = '__all__'
        widgets = {
            "config": Textarea(attrs={"style": "width:70%;background:#FDF5E6", "placeholder": "请粘贴配置"}),
        }
