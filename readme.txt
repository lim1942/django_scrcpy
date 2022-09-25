django_scrcpy

基于python3.7, django异步框架，后端scrcpy_server.jar获取手机h264流，视频推流采用websocket，前端broardway.js播放h264流。
先配置好adb，手机设备打开usb调试并连接项目所在的电脑主机。
经测试在 720X336分辨率，800k比特率，25帧，本地浏览器延迟大概为30ms左右。

1.运行：
 (1).安装依赖
 pip install -r requirements.txt
 (2).生成sqlite数据库表结构
 python manage.py migrate
 (3).创建一个管理后台用户
 python manage.py createsuperuser
 (4).收集项目静态文件
 python manage.py collectstatic
 (5).设置关闭调试模式django_scrcpy/settings.py
 DEBUG = False
 (6).运行项目
 daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000
 (7).访问管理端登录管理手机
 http://127.0.0.1:8000/admin/
