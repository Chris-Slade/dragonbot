import asyncio
from aiohttp import web

async def handle_health(request):
    return web.Response(
        status=200,
        content_type='text/html',
        text="<html><head><title>Dragonbot</title></head><body>Healthy</body></html>",
    )

print('Starting web server')
app = web.Application()
app.add_routes([web.get('/', handle_health)])
web.run_app(app, port=10000)
