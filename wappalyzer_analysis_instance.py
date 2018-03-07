import logging
import os
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
            uri = 'http://{}'.format(sample.unique_features.domain)
        else:
            raise ValueError('Sample has neither an URI nor a domain.')

        log.info('Querying {}...'.format(uri))
        page = WebPage.new_from_url(uri, verify=False)
        results = self.wappalyzer.analyze(page)

        tags = []
        for app in results:
            app_name, version = app['name'].replace(' ', '-'), app['version']
            tags.append(app_name)
            if version:
                tags.append('{}:{}'.format(app_name, version))

        scheduled_analysis.create_report(tags=tags,
                                         json_report_objects={"wappalyzer_results": ("wappalyzer_results", results),
                                                              "headers": ("headers", dict(page.headers)),
                                                              "meta": ("meta", dict(page.meta))})


if __name__ == '__main__':
    api_key = os.getenv('MASS_API_KEY', '')
    log.info('Got API KEY {}'.format(api_key))
    server_addr = os.getenv('MASS_SERVER', 'http://localhost:8000/api/')
    log.info('Connecting to {}'.format(server_addr))
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))
    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)

    analysis_system_instance = get_or_create_analysis_system_instance(identifier='wappalyzer',
                                                                      verbose_name='Wappalyzer',
                                                                      tag_filter_exp='sample-type:uri or sample-type:domain'
                                                                      )
    process_analyses(analysis_system_instance, WappalyzerAnalysisInstance(), sleep_time=7, delete_instance_on_exit=True,
                     catch_exceptions=True)
