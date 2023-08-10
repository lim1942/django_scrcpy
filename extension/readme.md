# 一.Ready-made
`You do not need build, just prepara libav dependence`
- Linux(x64)  
    `sudo apt install libavcodec-dev libavformat-dev libavutil-dev libswresample-dev`
- Windows(x64)  
    Download [ffmpeg-win64](https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2022-02-28-12-30/ffmpeg-N-105793-ga0a2ccd55d-win64-gpl-shared.zip), then copy (avcodec-59.dll) , (avformat-59.dll) , (avutil-57.dll) , (swresample-4.dll) from *ffmpeg/bin* to this path.
# 二.Build
## 1 install cython
`pip install cython`
## 2.preparation
install gcc and ffmpeg....

## 3 build dynamic  lib
`python setup.py build_ext -i`
