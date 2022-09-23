django_scrcpy, 基于django异步框架，后端scrcpy_server.jar获取手机h264流，前端broardway.js播放h264流。
先配置好adb，手机设备打开usb调试并连接项目所在的电脑主机。

1.运行：
 (1).生成sqlite数据库表结构
 python manage.py migrate
 (2).创建一个管理后台用户
 python manage.py createsuperuser
 (3).收集项目静态文件
 python manage.py collectstatic
 (4).设置关闭调试模式django_scrcpy/settings.py
 DEBUG = False
 (5).运行项目
 daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000
 (6).访问管理端管理手机
 http://127.0.0.1:8000/admin/

2.需要新增的功能
(1).适配操作控制事件，剪切板获取`
(2).admin配置管理
(3).文件管理功能
(4).shell管理

3.注意
无线设备，如 192.168.1.6:5555，请替换成 192,168,1,6_5555