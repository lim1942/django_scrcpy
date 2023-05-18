run:
        daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000
build-recorder:
        gcc asset/recorder.c -lavcodec  -lavformat -lavutil  -o asset/recorder.out