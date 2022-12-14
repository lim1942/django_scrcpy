from django.db import models


class Mobile(models.Model):
    device_id = models.CharField("device_id", max_length=127, unique=True, null=False, blank=False)
    device_name = models.CharField('设备名', max_length=32, blank=True, null=False)
    device_type = models.CharField('设备类型', max_length=32, blank=True, null=False)
    config = models.TextField("配置详情", default='{}', help_text='配置视频分辨率，帧率等')
    details = models.TextField("备注信息", blank=True)
    updated_time = models.DateTimeField("更新时间", auto_now=True, db_index=True)
    created_time = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    def __str__(self):
        return self.device_id

    class Meta:
        verbose_name_plural = verbose_name = '手机'
        ordering = ('updated_time', 'created_time')
