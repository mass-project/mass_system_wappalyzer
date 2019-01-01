from aio import aio_handle_requests
from wappalyzer import Wappalyzer
from message_objects import SuccessfulResult, ExceptionResult

from setproctitle import setproctitle
from traceback import format_exc

from multiprocessing import Process, Queue, cpu_count
from datetime import datetime
import csv
import sys
import queue


def csv_input_reader(url_queue):
    with open('majestic_1000.csv') as csvfile:
    #with open('test_sites.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader)
        for row in reader:
            url = 'https://' + row[2] + '/'
            url_queue.put(url)
            #print("Enqueuing", url)


def txt_input_reader(url_queue):
    with open('test.txt') as fp:
        for url in fp:
            url_queue.put(url.strip())


def wappalyzer(wa, match_queue, result_queue):
    setproctitle("wappalyzer: wappalyzer")

    while True:
        response = match_queue.get()
        if not response:
            break

        try:
            matches = wa.match(response.content, response.headers)
            result_queue.put(SuccessfulResult(response.url, response.status, matches))
        except Exception as e:
            print("wappalyzer", response, e, file=sys.stderr)
            result_queue.put(ExceptionResult(response.url, e, format_exc()))


def result_writer(result_queue):
    setproctitle("wappalyzer: result_writer")

    written_total, written_last = 0, 0
    last_out = time_begin = datetime.now()
    with open("results.txt", "w") as fp_results, open("exceptions.txt", "w") as fp_exc, open("rates.txt", "w") as fp_rates:
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
            if isinstance(result, SuccessfulResult):
                print(result.serialize(), file=fp_results)
            else:
                print(result.serialize(), file=fp_exc)
            written_total += 1


def main():
    num_wa = cpu_count()
    num_fetch = 2
    num_connections = 100

    wa = Wappalyzer()
    url_queue, match_queue, result_queue = Queue(), Queue(), Queue()
    p_http_reciever = [Process(target=aio_handle_requests, args=(url_queue, match_queue, result_queue, num_connections/num_fetch)) for _ in range(num_fetch)]
    p_wappalyzer = [Process(target=wappalyzer, args=(wa, match_queue, result_queue)) for _ in range(num_wa)]
    p_result = Process(target=result_writer, args=(result_queue,))

    for p in p_http_reciever + [p_result] + p_wappalyzer:
        p.start()

    csv_input_reader(url_queue)
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
