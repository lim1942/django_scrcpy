run:
	daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000
stop:
	ps -ef | grep "daphne django_scrcpy.asgi:application -b 0.0.0.0 -p 8000" | grep -v grep | awk '{print $$2}' | xargs kill -9
restart:
	make stop && make
build_recorder:
	gcc asset/recorder.c -lavcodec  -lavformat -lavutil  -o asset/recorder.out
docker_build:
	docker build . -t lim1942/django_scrcpy:1.0
docker_run:
	docker run -it --name django_scrcpy -p 8000:8000 -e ADB_SERVER_ADDR=docker.for.mac.localhost -e ADB_SERVER_ADDR=5037 lim1942/django_scrcpy:1.0
docker_start:
	docker start django_scrcpy
docker_stop:
	docker stop django_scrcpy
docker_restart:
	docker restart django_scrcpy
docker_remove:
	make docker_stop && docker rm django_scrcpy