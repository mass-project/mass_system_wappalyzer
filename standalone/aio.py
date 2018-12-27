from message_objects import Response

import asyncio
import uvloop
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiohttp.resolver import AsyncResolver
import socket
import sys


async def fetch(url, result_queue):
    try:
        #print('Fetching ', url)
        timeout = ClientTimeout(total=5, connect=None, sock_connect=None, sock_read=None)
        resolver = AsyncResolver()
        conn = TCPConnector(resolver=resolver, family=socket.AF_INET, limit=0, verify_ssl=False)
        async with ClientSession(connector=conn, timeout=timeout) as session:
            async with session.get(url, allow_redirects=True) as response:
                headers = {k: v for k, v in response.headers.items()}
                r = Response(response.status, headers, url, await response.read())
                result_queue.put(r)
    except Exception as e:
        print("fetch", url, e, file=sys.stderr)


async def bound_fetch(sem, url, result_queue):
    async with sem:
        await fetch(url, result_queue)


async def run_requests(loop, url_queue, result_queue, num_connections):
    requests = []
    sem = asyncio.Semaphore(num_connections)

    while True:
        url = url_queue.get()

        # Fetch the None to end the processing
        if not url:
            break

        task = asyncio.ensure_future(bound_fetch(sem, url, result_queue))
        requests.append(task)

    await asyncio.gather(*requests)


def aio_handle_requests(url_queue, result_queue, num_connections):
    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_requests(loop, url_queue, result_queue, num_connections))
