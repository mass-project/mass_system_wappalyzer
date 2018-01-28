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
            uri = 'https://{}'.format(sample.unique_features.domain)
        else:
            raise ValueError('Sample has neither an URI nor a domain.')

        log.info('Querying {}...'.format(uri))
        page = WebPage.new_from_url(uri)
        apps = self.wappalyzer.analyze_with_categories(page)

        # Restructure results
        apps_by_category = {}
        for k, v in apps.items():
            for category in v['categories']:
                if category['name'] in apps_by_category:
                    apps_by_category[category['name']].append(k)
                else:
                    apps_by_category[category['name']] = [k]

        scheduled_analysis.create_report(additional_metadata=apps_by_category)


if __name__ == '__main__':
    api_key = os.getenv('MASS_API_KEY', '')
    log.info('Got API KEY {}'.format(api_key))
    server_addr = os.getenv('MASS_SERVER', 'http://localhost:8000/api/')
    log.info('Connecting to {}'.format(server_addr))
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))
    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)

    analysis_system_instance = get_or_create_analysis_system_instance(identifier='wappalyzer',
                                                                      verbose_name='Wappalyzer',
                                                                      tag_filter_exp='sample-type:urisample'
                                                                      )
    process_analyses(analysis_system_instance, WappalyzerAnalysisInstance(), sleep_time=7, delete_instance_on_exit=True,
                     catch_exceptions=True)
