

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


async def VideoWsHandle(scope, receive, send):
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


async def ControlWsHandle(scope, receive, send):
    while True:
        event = await receive()
        if event['type'] == 'websocket.connect':
            await send({
                'type': 'websocket.accept'
            })
            print('ControlWsHandle')

        if event['type'] == 'websocket.disconnect':
            break

        if event['type'] == 'websocket.receive':
            print(event['text'])
            await send({
                'type': 'websocket.send',
                'text': 'send'
            })