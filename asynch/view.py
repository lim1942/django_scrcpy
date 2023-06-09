import os
import re

import mimetypes
import aiofiles
from ninja import NinjaAPI

from django.shortcuts import render
from django.urls import reverse
from django.http import StreamingHttpResponse
from django_scrcpy.settings import MEDIA_ROOT


api = NinjaAPI(urls_namespace='asynch')


async def file_iterator(file_name, chunk_size=8192*100, offset=0, length=None):
        async with aiofiles.open(file_name, "rb") as f:
            await f.seek(offset)
            remaining = length
            while True:
                bytes_length = chunk_size if remaining is None else min(remaining, chunk_size)
                data = await f.read(bytes_length)
                if not data:
                    break
                if remaining:
                    remaining -= len(data)
                yield data


@api.get("/video/play", url_name='video-play')
async def video_play(request, filename: str) ->str:
    play_url = reverse("asynch:video-stream") + f"?filename={filename}"
    kwargs = {"filename": filename, "play_url": play_url}
    return render(request, "asynch/video_play.html", kwargs)


@api.get("/video/stream", url_name='video-stream')
async def video_stream(request, filename: str) -> str:
    full_filename = os.path.join(MEDIA_ROOT, "video", filename)
    range_header = request.META.get('HTTP_RANGE', '').strip()
    range_re = re.compile(r'bytes\s*=\s*(\d+)\s*-\s*(\d*)', re.I)
    range_match = range_re.match(range_header)
    size = os.path.getsize(full_filename)
    if range_match:
        content_type, encoding = mimetypes.guess_type(full_filename)
        content_type = content_type or 'application/octet-stream'
        first_byte, last_byte = range_match.groups()
        first_byte = int(first_byte) if first_byte else 0
        last_byte = first_byte + 1024 * 1024 * 8  # 8M 每片,响应体最大体积
        if last_byte >= size:
            last_byte = size - 1
        length = last_byte - first_byte + 1
        resp = StreamingHttpResponse(file_iterator(full_filename, offset=first_byte, length=length), status=206, content_type=content_type)
        resp['Content-Length'] = str(length)
        resp['Content-Range'] = 'bytes %s-%s/%s' % (first_byte, last_byte, size)
    else:
        content_type = 'application/octet-stream'
        resp = StreamingHttpResponse(file_iterator(full_filename), content_type=content_type)
        resp['Content-Length'] = str(size)
        resp['Content-Disposition'] = 'attachment;filename="%s"' % os.path.basename(filename)
    resp.is_async = True
    resp['Accept-Ranges'] = 'bytes'
    return resp
