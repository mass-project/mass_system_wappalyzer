import logging
import warnings
import os
import requests
from urllib3.exceptions import InsecureRequestWarning
from wappalyzer import Wappalyzer, WebPage
from mass_api_client import ConnectionManager
from mass_api_client.utils import process_analyses, get_or_create_analysis_system_instance

logging.basicConfig()
log = logging.getLogger('wappalyzer_analysis_system')
log.setLevel(logging.INFO)


class WappalyzerAnalysisInstance:
    def __init__(self):
        self.wappalyzer = Wappalyzer.latest()

    def __call__(self, scheduled_analysis):
        sample = scheduled_analysis.get_sample()

        # Check if there is a specific uri given, otherwise construct one from the domain
        if sample.has_uri():
            uri = sample.unique_features.uri
        elif sample.has_domain():
            uri = 'https://{}'.format(sample.unique_features.domain)
        else:
            raise ValueError('Sample has neither an URI nor a domain.')

        log.info('Querying {}...'.format(uri))
        warnings.simplefilter('ignore', InsecureRequestWarning)
        response = requests.get(uri, allow_redirects=True, verify=False, timeout=7)
        page = WebPage.new_from_response(response)
        results = self.wappalyzer.analyze(page)
        status_code = response.status_code

        tags = [
            'wappalyzer-http-status:{}'.format(status_code)
        ]
        for app in results:
            app_name, version = app['name'].replace(' ', '-'), app['version']
            tags.append(app_name)
            if version:
                tags.append('{}:{}'.format(app_name, version))

        redirects = [(r.url, r.status_code) for r in response.history]
        failed_status = status_code > 500

        metadata = {
            'status': status_code,
            'url': page.url,
            'redirects': len(redirects)
        }

        scheduled_analysis.create_report(tags=tags, failed=failed_status, additional_metadata=metadata,
                                         json_report_objects={"wappalyzer_results": ("wappalyzer_results", results),
                                                              "headers": ("headers", dict(page.headers)),
                                                              "meta": ("meta", dict(page.meta)),
                                                              "redirects": ("redirects", redirects),
                                                              "cookies": ("cookies", dict(response.cookies))})


if __name__ == '__main__':
    api_key = os.getenv('MASS_API_KEY', '')
    log.info('Got API KEY {}'.format(api_key))
    server_addr = os.getenv('MASS_SERVER', 'http://localhost:8000/api/')
    log.info('Connecting to {}'.format(server_addr))
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))
    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)

    analysis_system_instance = get_or_create_analysis_system_instance(identifier='wappalyzer',
                                                                      verbose_name='Wappalyzer',
                                                                      tag_filter_exp='sample-type:uri or sample-type:domain',
                                                                      time_schedule=[0, 5, 30, 60]
                                                                      )
    process_analyses(analysis_system_instance, WappalyzerAnalysisInstance(), sleep_time=7, delete_instance_on_exit=True,
                     catch_exceptions=True)
