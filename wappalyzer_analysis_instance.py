import asyncio
import logging
import os
import re

import uvloop
from mass_api_client import ConnectionManager
from mass_api_client.utils import get_or_create_analysis_system
from mass_api_client.utils.multistaged_analysis import AnalysisFrame
from mass_api_client.utils.multistaged_analysis.miscellaneous import report, get_requests, get_http

from wappalyzer import Wappalyzer, WebPage

logging.basicConfig()
log = logging.getLogger('wappalyzer_analysis_system')
log.setLevel(logging.INFO)


class WappalyzerAnalysisInstance:
    def __init__(self):
        self.wappalyzer = Wappalyzer.latest()

    @staticmethod
    def prepare_domain_or_url(sockets):
        data = sockets.receive()
        sample = data.sample
        # Check if there is a specific uri given, otherwise construct one from the domain
        if sample.has_uri():
            uri = sample.unique_features.uri
        elif sample.has_domain():
            uri = 'https://{}'.format(sample.unique_features.domain)
            if 'wildcard_true' in sample.tags:
                uri = uri.replace('*.', '')
        else:
            print('Sample has neither an URI nor a domain.')
            data.report['tags'] = ['no_url_or_domain']
            data.report['failed'] = True
            sockets.send(data, stage='report')
            return
        sockets.send_with_instruction(data, 'get_http', 'request', {'url_list': [uri],
                                                                    'text': True,
                                                                    'headers': True,
                                                                    'status': True,
                                                                    'cookies': True,
                                                                    'redirects': True,
                                                                    'stream': True,
                                                                    'client_headers': {
                                                                        'User-Agent': 'Mozilla/5.0 (Wappalyzer)'}
                                                                    }, stage_instruction='wappalyzer')

    def __call__(self, sockets):
        data = sockets.receive()
        html = data.get_stage_report('request')[0]['text']
        headers = data.get_stage_report('request')[0]['headers']
        status_code = data.get_stage_report('request')[0]['status']
        url = data.get_stage_report('request')[0]['url']
        cookies = data.get_stage_report('request')[0]['cookies']
        redirects = data.get_stage_report('request')[0]['redirects']
        page = WebPage(url, html=html, headers=headers)
        results = self.wappalyzer.analyze(page)
        status_code = status_code

        tags = [
            'wappalyzer-http-status:{}'.format(status_code)
        ]

        tag_validator = re.compile(r'[^\w:\-\_\/\+\.]+')
        for app in results:
            app_name, version = app['name'].replace(' ', '-'), app['version'].replace(' ', '-')
            app_name, version = tag_validator.sub('', app_name), tag_validator.sub('_', version)

            tags.append(app_name)
            if version:
                tags.append('{}:{}'.format(app_name, version))

        if status_code < 400:
            if results:
                tags.append('wappalyzer-found-apps')
            else:
                tags.append('wappalyzer-found-nothing')
        failed_status = status_code > 500

        metadata = {
            'status': status_code,
            'url': page.url,
            'redirects': redirects
        }

        data.report['tags'] = tags
        data.report['additional_metadata'] = metadata
        data.report['failed'] = failed_status
        data.report['json_report_objects'] = {"wappalyzer_results": results,
                                              "headers": dict(page.headers),
                                              "meta": dict(page.meta),
                                              "redirects": redirects,
                                              "cookies": cookies}

        sockets.send(data)


if __name__ == '__main__':
    api_key = os.getenv('MASS_API_KEY', 'IjViNzE2MmM1ZTI3Yzk1N2I2ZDAwZWExNyI.163yDtI2y-t7DrMxIFYvTwo8s2Q')
    log.info('Got API KEY {}'.format(api_key))
    server_addr = os.getenv('MASS_SERVER', 'http://127.0.0.1:8000/api/')
    log.info('Connecting to {}'.format(server_addr))
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))
    stream_timeout = int(os.getenv('WA_STREAM_TIMEOUT', '10'))
    wappalyzer_concurrency = int(os.getenv('WA_CONCURRENCY', '8'))
    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)
    analysis_system = get_or_create_analysis_system(identifier='wappalyzer',
                                                    verbose_name='Wappalyzer',
                                                    tag_filter_exp='sample-type:uri or sample-type:domain',
                                                    time_schedule=[0, 5, 30, 60]
                                                    )
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    frame = AnalysisFrame()
    frame.add_stage(get_requests, 'get_requests', concurrency='process', args=(analysis_system,), next_stage='prepare')
    frame.add_stage(WappalyzerAnalysisInstance.prepare_domain_or_url, 'prepare', concurrency='process')
    frame.add_stage(get_http, 'get_http', concurrency='async')
    frame.add_stage(WappalyzerAnalysisInstance(), 'wappalyzer', concurrency='process', next_stage='report',
                    replicas=wappalyzer_concurrency)
    frame.add_stage(report, 'report', concurrency='process')
    frame.start_all_stages()
