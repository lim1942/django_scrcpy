django_scrcpy, 基于django异步框架，后端scrcpy_server.jar获取手机h264流，前端broardway.js播放h264流。

1.运行：
    daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000

2.需要新增的功能
(1).适配操作控制事件，剪切板获取`
(2).admin配置管理
(3).文件管理功能
(4).shell管理

3.注意
无线设备，如 192.168.1.6:5555，请替换成 192,168,1,6_5555