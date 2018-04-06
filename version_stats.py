from mass_api_client import ConnectionManager
from mass_api_client.resources import Sample
from collections import Counter
import os
import re
from pprint import pprint


def _clean_app_name(app_name):
    tag_validator = re.compile(r'[^\w:\-\_\/\+\.]+')
    app_name = app_name.replace(' ', '-')
    return tag_validator.sub('', app_name)


def get_counts(app_name):
    versions = []
    app_name = _clean_app_name(app_name)
    for sample in Sample.query(tags__contains=app_name):
        for tag in sample.tags:
            if tag.startswith('{}:'.format(app_name)):
                versions.append(tag)
        else:
            versions.append(None)

    return Counter(versions)


if __name__ == '__main__':
    api_key = os.getenv('MASS_API_KEY', '')
    server_addr = os.getenv('MASS_SERVER', '')
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))

    ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)
    pprint(get_counts('Drupal'))


