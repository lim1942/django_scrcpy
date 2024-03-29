# Generated by Django 3.2.18 on 2023-05-19 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general', '0002_remove_mobile_online'),
    ]

    operations = [
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('video_id', models.CharField(db_index=True, max_length=127, unique=True, verbose_name='video_id')),
                ('device_id', models.CharField(db_index=True, max_length=127, verbose_name='device_id')),
                ('format', models.CharField(db_index=True, max_length=32, verbose_name='文件格式')),
                ('duration', models.IntegerField(verbose_name='视频时长')),
                ('size', models.IntegerField(verbose_name='视频大小')),
                ('start_time', models.DateTimeField(db_index=True, verbose_name='开始时间')),
                ('finish_time', models.DateTimeField(db_index=True, verbose_name='结束时间')),
                ('config', models.TextField(default='{"recorder": true, "recorder_mkv": true, "log_level": "verbose", "audio": true, "video_codec": "h264", "audio_codec": "opus", "max_size": 720, "video_bit_rate": 800000, "audio_bit_rate": 128000, "max_fps": 25, "lock_video_orientation": -1, "tunnel_forward": true, "crop": "", "control": true, "show_touches": false, "stay_awake": true, "video_codec_options": "profile=1,level=2", "audio_codec_options": "", "video_encoder": "OMX.google.h264.encoder", "audio_encoder": "c2.android.opus.encoder", "power_off_on_close": false, "clipboard_autosync": false, "downsize_on_error": true, "cleanup": true, "power_on": true, "list_encoders": false, "list_displays": false, "send_device_meta": true, "send_frame_meta": true, "send_dummy_byte": true, "send_codec_meta": true, "raw_video_stream": false}', help_text='配置视频分辨率，帧率等', verbose_name='配置详情')),
            ],
            options={
                'verbose_name': '视频',
                'verbose_name_plural': '视频',
                'ordering': ('-finish_time',),
            },
        ),
        migrations.AlterField(
            model_name='mobile',
            name='config',
            field=models.TextField(default='{"recorder": true, "recorder_mkv": true, "log_level": "verbose", "audio": true, "video_codec": "h264", "audio_codec": "opus", "max_size": 720, "video_bit_rate": 800000, "audio_bit_rate": 128000, "max_fps": 25, "lock_video_orientation": -1, "tunnel_forward": true, "crop": "", "control": true, "show_touches": false, "stay_awake": true, "video_codec_options": "profile=1,level=2", "audio_codec_options": "", "video_encoder": "OMX.google.h264.encoder", "audio_encoder": "c2.android.opus.encoder", "power_off_on_close": false, "clipboard_autosync": false, "downsize_on_error": true, "cleanup": true, "power_on": true, "list_encoders": false, "list_displays": false, "send_device_meta": true, "send_frame_meta": true, "send_dummy_byte": true, "send_codec_meta": true, "raw_video_stream": false}', help_text='配置视频分辨率，帧率等', verbose_name='配置详情'),
        ),
        migrations.AlterField(
            model_name='mobile',
            name='details',
            field=models.TextField(blank=True, verbose_name='备注信息'),
        ),
    ]
