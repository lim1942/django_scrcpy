From python:3.7.16

# copy files
WORKDIR /usr/src/app
COPY . .

#  recoder
RUN sed -i s@/archive.ubuntu.com/@/mirrors.aliyun.com/@g /etc/apt/sources.list
RUN sed -i s@/deb.debian.org/@/mirrors.aliyun.com/@g /etc/apt/sources.list 
RUN apt-get clean && apt update
RUN apt install -y gcc libavcodec-dev libavdevice-dev libavformat-dev libavutil-dev libswresample-dev 
RUN apt-get clean all
RUN gcc asset/recorder.c -lavcodec  -lavformat -lavutil  -o asset/recorder.out

# python
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip cache purge
RUN cp asset/db.sqlite3 ./db.sqlite3

# run
CMD ["daphne", "django_scrcpy.asgi:application", "-b", "0.0.0.0", "-p", "8000"]