from message_objects import Response, ExceptionResult

from setproctitle import setproctitle

import asyncio
import aiojobs
import uvloop
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiohttp.resolver import AsyncResolver
import socket

from traceback import format_exc
from queue import Empty


async def fetch(url, match_queue, result_queue, resolver):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"}
        conn = TCPConnector(resolver=resolver, family=socket.AF_INET, limit=100, verify_ssl=False, enable_cleanup_closed=True, force_close=True)
        timeout = ClientTimeout(total=5, connect=None, sock_connect=None, sock_read=None)
        async with ClientSession(connector=conn, timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                headers = {k: v for k, v in response.headers.items()}
                content = await response.read()
                r = Response(response.status, headers, url, content.decode('utf-8', 'ignore'))
                match_queue.put(r)
    except Exception as e:
        result_queue.put(ExceptionResult(url, e, format_exc()))


async def bound_fetch(sem, url, match_queue, result_queue, resolver):
    async with sem:
        await fetch(url, match_queue, result_queue, resolver)


async def run_requests(loop, url_queue, match_queue, result_queue, num_connections, nameserver):
    scheduler = await aiojobs.create_scheduler(limit=num_connections)
    resolver = AsyncResolver(nameservers=[nameserver]) if nameserver else AsyncResolver()

    while True:
        try:
            url = url_queue.get(timeout=0.1)
        except Empty:
            await asyncio.sleep(1)
            continue

        # Fetch the None to end the processing
        if not url:
            break

        job = await scheduler.spawn(fetch(url, match_queue, result_queue, resolver))

    # TODO: Find out why this workaround is necessary
    await job.wait()
    await asyncio.sleep(10)
    await scheduler.close()


def aio_handle_requests(url_queue, match_queue, result_queue, num_connections, nameserver=None):
    setproctitle("wappalyzer: aio_handle_requests")

    loop = asyncio.get_event_loop()
    #loop = uvloop.new_event_loop()
    #asyncio.set_event_loop(loop)
    loop.run_until_complete(run_requests(loop, url_queue, match_queue, result_queue, num_connections, nameserver))
