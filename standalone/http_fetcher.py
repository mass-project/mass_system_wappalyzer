from aio import aio_handle_requests
from wappalyzer import Wappalyzer
from message_objects import SuccessfulResult, ExceptionResult

from setproctitle import setproctitle
from traceback import format_exc

from multiprocessing import Process, Queue, Value
from datetime import datetime
from time import sleep
import csv
import sys
import queue
import traceback


def _wait_for_queue_limit(read_total, written_total, watermark_low, watermark_high):
    if read_total > written_total.value + watermark_high:
        while read_total > written_total.value + watermark_low:
            sleep(0.1)


def csv_input_reader(url_queue, written_total, watermark_low, watermark_high):
    with open('majestic_1000.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader)
        for read_total, row in enumerate(reader):
            _wait_for_queue_limit(read_total, written_total, watermark_low, watermark_high)
            url = 'https://' + row[2] + '/'
            url_queue.put(url)


def txt_input_reader(url_queue, written_total, watermark_low, watermark_high):
    with open('wordpress.txt') as fp:
        for read_total, url in enumerate(fp):
            _wait_for_queue_limit(read_total, written_total, watermark_low, watermark_high)
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
            traceback.print_exc(file=sys.stderr)
            print("wappalyzer", response, e, file=sys.stderr)
            result_queue.put(ExceptionResult(response.url, e, format_exc()))


def result_writer(url_queue, match_queue, result_queue, written_total):
    setproctitle("wappalyzer: result_writer")
    refresh_rate = 1

    written_last, successful, successful_last = 0, 0, 0
    last_out = time_begin = datetime.now()
    with open("results.txt", "w") as fp_results, open("exceptions.txt", "w") as fp_exc, open("rates.txt", "w") as fp_rates:
        while True:
            delta_seconds = (datetime.now() - last_out).total_seconds()
            if delta_seconds > refresh_rate:
                time_total = (datetime.now() - time_begin).total_seconds()
                args = {
                    "results": (written_total.value-written_last)/delta_seconds,
                    "successes": (successful-successful_last)/delta_seconds,
                    "errors": (written_total.value-successful-written_last+successful_last)/delta_seconds,
                    "success_rate": (successful-successful_last)*100/(written_total.value-written_last) if written_total.value > 0 else 0,
                    "num": written_total.value,
                    "time": time_total,
                    "url_queue": url_queue.qsize(),
                    "match_queue": match_queue.qsize(),
                    "result_queue": result_queue.qsize()
                }
                print("Results:\t{results:.2f}/s\t\tSuccesses:\t{successes:.2f}/s\t\tErrors:\t{errors:.2f}/s\t\t".format(**args) +
                      "Queues:\t{url_queue}/{match_queue}/{result_queue}\t\t".format(**args) +
                      "Success Rate:\t{success_rate:.2f}%\t\tTime:\t{time:.2f}\t\tTotal results:\t{num}".format(**args))
                print("{time}\t{num}\t{results}\t{successes}\t{errors}\t{success_rate}".format(**args), file=fp_rates)
                written_last = written_total.value
                successful_last = successful
                last_out = datetime.now()

            try:
                result = result_queue.get(timeout=refresh_rate)
            except queue.Empty:
                continue

            if not result:
                break
            if isinstance(result, SuccessfulResult):
                print(result.serialize(), file=fp_results)
                successful += 1
            else:
                print(result.serialize(), file=fp_exc)
            written_total.value += 1


def main():
    num_wa = 2
    num_fetch = 12
    num_connections = 5000

    wa = Wappalyzer()
    url_queue, match_queue, result_queue = Queue(), Queue(), Queue()
    written_total = Value('i', 0)
    p_http_reciever = [Process(target=aio_handle_requests, args=(url_queue, match_queue, result_queue, num_connections/num_fetch)) for _ in range(num_fetch)]
    p_wappalyzer = [Process(target=wappalyzer, args=(wa, match_queue, result_queue)) for _ in range(num_wa)]
    p_result = Process(target=result_writer, args=(url_queue, match_queue, result_queue, written_total))

    for p in p_http_reciever + [p_result] + p_wappalyzer:
        p.start()

    csv_input_reader(url_queue, written_total, 3000, 10000)
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
