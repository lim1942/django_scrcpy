# 简介(What we can do)
![](https://img.shields.io/badge/windows-grey)
![](https://img.shields.io/badge/linux-grey)
![](https://img.shields.io/badge/python-3.7-green)  
实现安卓设备的web投屏和操控，提供一个配置管理页用于配置各设备的投屏参数(帧率，尺寸等),支持多设备。  
Android Device remote display and control in browser page.   
Provide manage site to configure display(frame-rate,screen-size,bit-rate), support multi devices.  
- web scrcpy
- file manage

![image](asset/device.png)
![image](asset/admin.png)

# 原理(Summary) 
后端用scrcpy_server.jar获取手机h264流, 传输通过websocket(django高效异步)，前端broardway.js播放h264流并捕获鼠标事件完成操控。
电脑先配置好adb，手机设备打开usb调试并连接项目所在的电脑主机, 经测试在usb2.0, 720X336分辨率，800k比特率，25帧，本地浏览器延迟大概为60ms左右。   
Backend scrcpy_server.jar grab android-device screen-raw-h264 data.  
Transmission based on websocket (Django efficiently asynchronous coroutine).  
Frontend broardway.js play screen-raw-h264 data, capture mouse`s event to control.
We test in local browser[usb2.0, 720x336, 800kbit/s, 25fps] delay average 60ms.


# 运行(Usage)：
>Make sure adb server started and android-device(in Developer Mode) has connected to adb server.  
> `adb devices` in command line can list connected device.    
> _**List of devices attached**_   
> **_ba406a9e0421    device_**
- Install    
 `pip install -r requirements.txt`  
 `python init.py`
- Run（Visit http://127.0.0.1:8000/admin）  
`daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000`
