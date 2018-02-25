from wappalyzer import Wappalyzer, WebPage
from urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import ConnectTimeout, ConnectionError, InvalidURL, ReadTimeout, TooManyRedirects
from multiprocessing import Pool
from collections import Counter
from pprint import pprint
import time
import warnings
import os


def analyze_domain(d):
    return analyze_url('https://{}'.format(d))


def analyze_url(url):
    try:
        page = WebPage.new_from_url(url, verify=False)
    except (ConnectTimeout, ConnectionError, ReadTimeout, InvalidURL, TooManyRedirects):
        #print('PID{}, {}: Could not connect'.format(os.getpid(), d))
        return 1, 0, set()
    except Exception:
        print('-'*20)
        print('Exception analyzing {}'.format(d))
        print('-'*20)
        raise

    apps = wa.analyze(page)
    #print('PID{}, {}: {}'.format(os.getpid(), d, apps))
    #print({"urls": [url],
    #       "applications": apps})

    if not apps:
        return 0, 1, apps
    else:
        return 0, 0, apps


if __name__ == '__main__':
    warnings.simplefilter('ignore', InsecureRequestWarning)
    wa = Wappalyzer.latest()
    #print(analyze_url("http://localhost:8000/webui/sample/5a70552415b77f06c144762d/")[2])

    with open('domains_small.txt') as fp:
        domains = fp.read().splitlines()

    start = time.time()

    with Pool(12) as p:
        results = p.map(analyze_domain, domains)
    #results = [analyze_domain(d) for d in domains]
    end = time.time()

    empty_sets, conn_errors, app_list = 0, 0, []
    for con, empty, apps in results:
        conn_errors += con
        empty_sets += empty
        app_list += list(apps)

    #pprint(Counter(app_list))
    #for i, d in enumerate(domains):
    #    analyze_domain(i, d)

    print('Checked {} domains in {}: {} without apps, {} unreachable.'.format(len(domains), end - start, empty_sets, conn_errors))
