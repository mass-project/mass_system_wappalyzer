from mass_api_client import ConnectionManager
from mass_api_client.resources import Sample
from collections import Counter
from pprint import pprint
import os
import time
import json


def count_tags():
    last_time = time.time()
    num_samples = 0
    tags = []
    for sample in Sample.items(page_size=1500):
        tags += sample.tags
        num_samples += 1
        if time.time() - last_time > 10:
            last_time = time.time()
            print(num_samples)

    return Counter(tags)


if __name__ == '__main__':
    api_key = os.getenv('MASS_API_KEY', '')
    server_addr = os.getenv('MASS_SERVER', '')
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))

    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)

    counts = count_tags()
    pprint(counts)

    with open('count_all_tags_results.json', 'w') as fp:
        json.dump(counts, fp)
