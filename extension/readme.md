# 一.preparation

## 1 install cython
`pip install cython`
## 2.install gcc & libav
- Linux(x64)  
    `sudo apt install libavcodec-dev libavformat-dev libavutil-dev libswresample-dev`
- Windows(x64)  
    Install ffmpeg, copy (avcodec-\*.dll) , (avformat-\*.dll) , (avutil-\*.dll) , (swresample-\*.dll) from *ffmpeg/bin* to this path.
# 二.build
    python setup.py build_ext -i 
