from aio import aio_handle_requests
from wappalyzer import Wappalyzer

from setproctitle import setproctitle

from multiprocessing import Process, Queue, cpu_count
from datetime import datetime, timedelta
import csv
import sys
import queue


def input_reader(url_queue):
    with open('majestic_million.csv') as csvfile:
    #with open('test_sites.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader)
        for row in reader:
            url = 'https://' + row[2] + '/'
            url_queue.put(url)
            #print("Enqueuing", url)


def wappalyzer(wa, in_queue, out_queue):
    setproctitle("wappalyzer: wappalyzer")

    while True:
        response = in_queue.get()
        #print(response)
        if not response:
            break

        try:
            matches = wa.match(response.content.decode(), response.headers)
            out_queue.put({'status': response.status, 'url': response.url, 'matches': matches})
        except Exception as e:
            print("wappalyzer", response, e, file=sys.stderr)


def result_writer(result_queue):
    setproctitle("wappalyzer: result_writer")

    written_total, written_last = 0, 0
    last_out = time_begin = datetime.now()
    with open("results.txt", "w") as fp_results, open("rates.txt", "w") as fp_rates:
        while True:
            delta_seconds = (datetime.now() - last_out).total_seconds()
            if delta_seconds > 1:
                time_total = (datetime.now() - time_begin).total_seconds()
                args = {"rate": (written_total-written_last)/delta_seconds, "num": written_total, "time": time_total}
                print("Time:\t{time:.2f}\t\tResult rate:\t{rate:.2f}/s\t\tTotal results:\t{num}".format(**args))
                print("{time}\t{rate}\t{num}".format(**args), file=fp_rates)
                written_last = written_total
                last_out = datetime.now()

            try:
                result = result_queue.get(timeout=1)
            except queue.Empty:
                continue

            if not result:
                break
            print(result, file=fp_results)
            written_total += 1


def main():
    num_wa = 2
    num_fetch = 7
    num_connections = 1800

    wa = Wappalyzer()
    url_queue, match_queue, result_queue = Queue(), Queue(), Queue()
    p_http_reciever = [Process(target=aio_handle_requests, args=(url_queue, match_queue, num_connections/num_fetch)) for _ in range(num_fetch)]
    p_wappalyzer = [Process(target=wappalyzer, args=(wa, match_queue, result_queue)) for _ in range(num_wa)]
    p_result = Process(target=result_writer, args=(result_queue,))

    for p in p_http_reciever + [p_result] + p_wappalyzer:
        p.start()

    input_reader(url_queue)
    for _ in range(num_fetch):
        url_queue.put(None)

    for p in p_http_reciever:
        p.join()

    for _ in range(num_wa):
        match_queue.put(None)

    for p in p_wappalyzer:
        p.join()

    result_queue.put(None)
    p_result.join()


if __name__ == '__main__':
    main()
