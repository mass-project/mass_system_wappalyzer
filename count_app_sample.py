from mass_api_client import ConnectionManager
from mass_api_client.resources import Sample
import json
import os
import re


def _clean_app_name(app_name):
    tag_validator = re.compile(r'[^\w:\-\_\/\+\.]+')
    app_name = app_name.replace(' ', '-')
    return tag_validator.sub('', app_name)


if __name__ == '__main__':
    with open('wappalyzer/data/apps.json') as fp:
        apps = json.load(fp)['apps']

    api_key = os.getenv('MASS_API_KEY', '')
    server_addr = os.getenv('MASS_SERVER', '')
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))

    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)

    counts = {}
    for app in apps.keys():
        tag = _clean_app_name(app)
        count = Sample.count(tags__contains=tag)
        counts[app] = count
        print('{}: {}'.format(tag, count))

    with open('count_app_results.json', 'w') as fp:
        json.dump(counts, fp)
