import asyncio

import aiofiles
from django.http import HttpResponse, StreamingHttpResponse,FileResponse
from django.views import View


async def file_iter(filename):
    async with aiofiles.open(filename, 'rb') as f:
        while True:
            chunk = await f.read(65536)
            if not chunk:
                break
            yield chunk


class AsyncView(View):
    async def get(self, request, *args, **kwargs):
        # Perform io-blocking view logic using await, sleep for example.
        iter_content = file_iter('/mnt/sdb1/develop/project/django_scrcpy/media/video/4de638df4afa4de99b7db7170ac38663.mp4')
        response = StreamingHttpResponse(streaming_content=iter_content, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment;filename="test.mp4"'
        response.is_async = True
        return response
