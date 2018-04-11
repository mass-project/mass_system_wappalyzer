import os
import json
from mass_api_client import ConnectionManager
from mass_api_client.resources import *
from multiprocessing import Pool, Manager, Queue, Process
from time import sleep
from os import getpid


def worker_process_sample(input_queue, output_queue):
    analysis_system = AnalysisSystem.get('crawl')
    n_reports = 0

    while True:
        sample = input_queue.get()
        n_reports += 1
        if n_reports % 500 == 0:
            print('[{}]: Processed 500 samples. Input-Queue size: {}, Output-Queue size: {}'.format(getpid(), input_queue.qsize(), output_queue.qsize()))

        if not sample:
            return

        for report in sample.get_reports():
            if report.analysis_system == analysis_system.url:
                output_queue.put((str(report.analysis_date), sample.tags))
                break
        else:
            print('No crawler report found for sample {}'.format(sample))


def result_worker(output_queue):
    results = []
    n_reports = 0

    while True:
        entry = output_queue.get()

        n_reports += 1
        if n_reports % 500 == 0:
            print('------> Result Worker: Processed 500 samples. Result-Queue size: {}, results: {}'.format(output_queue.qsize(), len(results)))

        if not entry:
            break

        results.append(entry)

    with open('process_report_data_results.json', 'w') as fp:
        json.dump(results, fp)


if __name__ == '__main__':
    api_key = os.getenv('MASS_API_KEY', '')
    server_addr = os.getenv('MASS_SERVER', '')
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))
    processes = int(os.getenv('MASS_PROCESSES', '16'))
    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)

    sample_queue = Queue(maxsize=2100)
    result_queue = Queue()

    processing_pool = Pool(processes, worker_process_sample, (sample_queue, result_queue))
    p = Process(target=result_worker, args=(result_queue,))
    p.start()

    n_samples = 0
    for sample in Sample.items(page_size=1000):
    #for sample in Sample.query(tags='Magento'):
        sample_queue.put(sample)
        n_samples += 1
        if n_samples % 500 == 0:
            print('Inserted 500 samples to sample queue. Size: {}'.format(sample_queue.qsize()))

    print('All samples enqueued')
    for _ in range(processes):
        sample_queue.put(None)

    # Wait till queue is empty
    while not sample_queue.empty():
        sleep(1)
        print('Waiting for sample queue to be empty')

    result_queue.put(None)
    p.join()