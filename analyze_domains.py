from wappalyzer import Wappalyzer, WebPage
from urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import ConnectTimeout, ConnectionError, InvalidURL, ReadTimeout, TooManyRedirects
from multiprocessing import Pool
from collections import Counter
from pprint import pprint
import time
import warnings
import os
import json
import logging
import requests

logging.basicConfig()
log = logging.getLogger('wappalyzer_analysis_system')
log.setLevel(logging.INFO)


def analyze_domain(d):
    return analyze_url('https://{}'.format(d))


def analyze_url(url):
    stream_timeout = 10
    try:
        log.info('Querying {}...'.format(url))
        warnings.simplefilter('ignore', InsecureRequestWarning)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Wappalyzer)'
        }
        response = requests.get(url, headers=headers, allow_redirects=True, verify=False, timeout=7, stream=True)

        start_time, html = time.time(), ''
        for chunk in response.iter_content(1024):
            if time.time() - start_time > stream_timeout:
                raise ValueError('Timeout reached. Downloading the contents took too long.')

            html += str(chunk)

        page = WebPage(response.url, html=html, headers=response.headers)
        apps = wa.analyze(page)
    except (ConnectTimeout, ConnectionError, ReadTimeout, InvalidURL, TooManyRedirects):
        # print('PID{}, {}: Could not connect'.format(os.getpid(), d))
        return 1, 0, set(), url
    except:
        print('-' * 20)
        print('Exception analyzing {}'.format(url))
        print('-' * 20)
        return 1, 0, set(), url

    # print('PID{}, {}: {}'.format(os.getpid(), d, apps))
#    print(json.dumps({"urls": [url],
#                      "applications": apps}))

    if not apps:
        return 0, 1, apps, url
    else:
        return 0, 0, apps, url


if __name__ == '__main__':
    warnings.simplefilter('ignore', InsecureRequestWarning)
    wa = Wappalyzer.latest()
    #analyze_url("https://www.computerbase.de/forum/")
    #exit(0)

    with open('domains.txt') as fp:
        domains = fp.read().splitlines()

    start = time.time()

    with Pool(24) as p:
        results = p.map(analyze_domain, domains)
    #results = [analyze_domain(d) for d in domains]
    end = time.time()

    empty_sets, conn_errors, app_list = 0, 0, {}
    for con, empty, apps, url in results:
        conn_errors += con
        empty_sets += empty
        app_list[url] = list(apps)

    # pprint(Counter(app_list))
    # for i, d in enumerate(domains):
    #    analyze_domain(i, d)

    print('Checked {} domains in {}: {} without apps, {} unreachable.'.format(len(domains), end - start, empty_sets,
                                                                              conn_errors))

    with open('wa_domain_results.txt', 'w') as fp:
        for d, apps in app_list.items():
            json.dump({'domain': d, 'apps': apps}, fp)
            fp.write('\n')
