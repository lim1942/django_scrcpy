# Generated by Django 3.2.18 on 2023-05-19 14:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('general', '0003_auto_20230519_1121'),
    ]

    operations = [
        migrations.CreateModel(
            name='Picture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_id', models.CharField(db_index=True, max_length=127, verbose_name='device_id')),
                ('picture', models.ImageField(upload_to='picture', verbose_name='截图')),
                ('size', models.IntegerField(verbose_name='图片大小(KB)')),
                ('created_time', models.DateTimeField(db_index=True, verbose_name='创建时间')),
            ],
        ),
        migrations.AlterModelOptions(
            name='video',
            options={'ordering': ('-finish_time',), 'verbose_name': '录屏', 'verbose_name_plural': '录屏'},
        ),
        migrations.AlterField(
            model_name='video',
            name='duration',
            field=models.IntegerField(verbose_name='视频时长(秒)'),
        ),
        migrations.AlterField(
            model_name='video',
            name='size',
            field=models.IntegerField(verbose_name='视频大小(KB)'),
        ),
    ]
