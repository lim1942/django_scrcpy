# ubuntu 录屏文档
## 1.安装录屏依赖
sudo apt install gcc libavcodec-dev libavdevice-dev libavformat-dev libavutil-dev libswresample-dev 
## 2.编译
gcc recorder.c -lavcodec  -lavformat -lavutil  -o recorder.out
## 3.实现
通过发送session_id连接recorder.py的socket服务，创建socket客户端，通过这个客户端接收流来实现录屏。