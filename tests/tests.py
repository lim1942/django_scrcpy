import asyncio
import time


async def LocalWsHandle(scope, receive, send):
    while True:
        print(receive)
        event = await receive()
        if event['type'] == 'websocket.connect':
            await send({
                'type': 'websocket.accept'
            })
        if event['type'] == 'websocket.disconnect':
            break

        if event['type'] == 'websocket.receive':
            print(event['text'])
            await send({
                'type': 'websocket.send',
                'text': 'send'
            })

async def test():
    print('#########')
    while True:
        time.sleep(1)
        print('-------')

async def VideoWsHandle(scope, receive, send):
    loop = asyncio.get_event_loop()
    while True:
        event = await receive()
        if event['type'] == 'websocket.connect':
            await send({
                'type': 'websocket.accept'
            })
            print('VideoWsHandle')

        if event['type'] == 'websocket.disconnect':
            break

        if event['type'] == 'websocket.receive':
            print(event['text'])
            await send({
                'type': 'websocket.send',
                'text': 'send'
            })
        loop.create_task(test())

async def ControlWsHandle(scope, receive, send):
    while True:
        event = await receive()
        if event['type'] == 'websocket.connect':
            await send({
                'type': 'websocket.accept'
            })


        if event['type'] == 'websocket.disconnect':
            break

        if event['type'] == 'websocket.receive':
            print(event['text'])
            await send({
                'type': 'websocket.send',
                'text': 'send'
            })