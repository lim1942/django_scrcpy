# ubuntu 录屏文档
## 1.安装录屏依赖
sudo apt install gcc libavcodec-dev libavdevice-dev libavformat-dev libavutil-dev libswresample-dev 
## 2.编译
gcc recorder.c -lavcodec  -lavformat -lavutil  -o recorder.out