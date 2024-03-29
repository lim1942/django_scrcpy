run:
	uvicorn django_scrcpy.asgi:application --host 0.0.0.0 --port 8000 --lifespan off
stop:
	lsof -i:8000 | grep "IPv4" | grep -v grep | awk '{print $$2}' | xargs kill -9
restart:
	make stop && make
build_recorder:
	gcc asset/recorder.c -lavcodec  -lavformat -lavutil  -o asset/recorder.out
docker_build:
	docker build . -t lim1942/django_scrcpy:1.0
docker_run:
	docker run -it --name django_scrcpy -v media:/usr/src/app/media --net=host lim1942/django_scrcpy:1.0
docker_start:
	docker start django_scrcpy
docker_stop:
	docker stop django_scrcpy
docker_restart:
	docker restart django_scrcpy
docker_remove:
	make docker_stop && docker rm django_scrcpy