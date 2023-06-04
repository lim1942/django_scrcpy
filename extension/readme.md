# 一.preparation
## 1 install cython
`pip install cython`
## 2.install gcc & libav
- linux  
    `sudo apt install gcc libavcodec-dev libavdevice-dev libavformat-dev libavutil-dev libswresample-dev`
- window  
    - Install visaul studio c environment ...
    - Install ffmpeg, add ffmpeg-bin to PATH, add ffmpeg-lib and ffmpeg-include to setup.py
# 二.build
    python setup.py build_ext -i 
