from mass_api_client import ConnectionManager
from mass_api_client.resources import Sample
from collections import Counter
import re
import json
from multiprocessing import Pool, Manager
import logging
import os

counter = None


def _clean_app_name(app_name):
    tag_validator = re.compile(r'[^\w:\-\_\/\+\.]+')
    app_name = app_name.replace(' ', '-')
    return tag_validator.sub('', app_name)


def get_counts(app_queue):
    counter_list = {}
    while True:
        results = []
        app_name = app_queue.get()
        if app_name is None:
            print('[{}] DONE.'.format(os.getpid()))
            return counter_list
        print('[{}] {} apps remaining: {}'.format(os.getpid(), app_name, app_queue.qsize()))
        count = None
        i = 0
        app_name = _clean_app_name(app_name)
        try:
            for sample in Sample.query(tags=app_name):
                i += 1
                if i % 5000 == 0:
                    if count is None:
                        count = Sample.count(tags=app_name)
                    print('[{}] {}/{} @{}'.format(os.getpid(), i, count, app_name))
                for tag in sample.tags:
                    if tag.startswith('{}:'.format(app_name)):
                        results.append(tag)
                results.append('Found')
            counter_list[app_name] = Counter(results)
        except:
            logging.error('[{}] EXCEPTION'.format(os.getpid()))
            continue


if __name__ == '__main__':
    api_key = os.getenv('MASS_API_KEY', '')
    server_addr = os.getenv('MASS_SERVER', '')
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))
    processes = int(os.getenv('MASS_PROCESSES', '16'))
    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)

    with open('wappalyzer/data/apps.json') as fp:
        apps = json.load(fp)['apps']
        m = Manager()
        queue = m.Queue()
        for app in apps:
            queue.put(app)
        for _ in range(processes):
            queue.put(None)
        with Pool(processes) as p:
            result_counters = p.map(get_counts, [queue for _ in range(processes)])
        end_result = {}
        for result_counter in result_counters:
            end_result = {**end_result, **result_counter}

    with open('count_app_results.json', 'w') as fp:
        json.dump(end_result, fp)

