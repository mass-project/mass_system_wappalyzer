from aio import aio_handle_requests
from wappalyzer import Wappalyzer

from multiprocessing import Process, Queue, cpu_count
import csv


def input_reader(url_queue):
    with open('majestic_1000.csv') as csvfile:
    #with open('test_sites.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader)
        for row in reader:
            url = 'https://' + row[2] + '/'
            url_queue.put(url)
            #print("Enqueuing", url)


def wappalyzer(wa, in_queue, out_queue):
    while True:
        response = in_queue.get(timeout=5)
        #print(response)
        if not response:
            break
        try:
            matches = wa.match(response.content.decode(), response.headers)
            out_queue.put({'status': response.status, 'url': response.url, 'matches': matches})
        except Exception as e:
            print(e)


def result_writer(queue):
    with open("results.txt", "w") as fp:
        while True:
            result = queue.get()
            #print("Writing ", result)
            if not result:
                break
            print(result, file=fp)


def main():
    num_wa = cpu_count()
    num_fetch = 2

    wa = Wappalyzer()
    url_queue, match_queue, result_queue = Queue(), Queue(), Queue()
    p_http_reciever = [Process(target=aio_handle_requests, args=(url_queue, match_queue)) for _ in range(num_fetch)]
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
