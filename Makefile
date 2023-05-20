run:
	daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000
stop:
	ps -ef | grep "daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000" | grep -v grep | awk '{print $$2}' | xargs kill -9
restart:
	make stop && make
build_recorder:
	gcc asset/recorder.c -lavcodec  -lavformat -lavutil  -o asset/recorder.out