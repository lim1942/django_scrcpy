FROM python:3.10.11

# copy files
WORKDIR /usr/src/app
COPY . .

#  recorder
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
RUN python manage.py collectstatic --noinput

# run
ENV DJANGO_SCRCPY_ADDR 0.0.0.0
ENV DJANGO_SCRCPY_PORT 8000
CMD uvicorn django_scrcpy.asgi:application --host $DJANGO_SCRCPY_ADDR --port $DJANGO_SCRCPY_PORT --workers 4 --lifespan off
