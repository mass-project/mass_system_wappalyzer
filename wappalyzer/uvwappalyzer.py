import csv
import asyncio
import uvloop
from uvhttp.http import Session
from uvhttp.dns import Resolver, DNSError

from hyperwapp import Wappalyzer


NUM_CONNS_PER_HOST = 100


async def do_request(sem, session, wa, url):
    async with sem:
        print("Request starting: {}".format(url))
        resp = await session.get(url.encode())
        print(url, wa.match(resp.text))
        #print("Request complete: {}".format(url))


async def main(loop, wa):
    resolver = Resolver(loop, ipv6=False)
    session = Session(NUM_CONNS_PER_HOST, loop, resolver=resolver)
    requests = []
    sem = asyncio.Semaphore(50)
    with open('majestic_1000.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader)
        for row in reader:
            url = 'https://' + row[2] + '/'
            task = asyncio.ensure_future(do_request(sem, session, wa, url))
            requests.append(task)
    try:
        await asyncio.gather(*requests, return_exceptions=True)
    except DNSError:
        print("DNS error!")


if __name__ == '__main__':
    wa = Wappalyzer()

    loop = uvloop.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main(loop, wa))
