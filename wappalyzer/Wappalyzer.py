"""
Original from https://github.com/chorsley/python-Wappalyzer
"""

import json
import re
import warnings
import logging
import pkg_resources

import requests

from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(name=__name__)


class WappalyzerError(Exception):
    """
    Raised for fatal Wappalyzer errors.
    """
    pass


class WebPage(object):
    """
    Simple representation of a web page, decoupled
    from any particular HTTP library's API.
    """

    def __init__(self, url, html, headers):
        """
        Initialize a new WebPage object.

        Parameters
        ----------

        url : str
            The web page URL.
        html : str
            The web page content (HTML)
        headers : dict
            The HTTP response headers
        """
        self.url = url
        self.html = html
        self.headers = headers

        try:
            self.headers.keys()
        except AttributeError:
            raise ValueError("Headers must be a dictionary-like object")

        self._parse_html()

    def _parse_html(self):
        """
        Parse the HTML with BeautifulSoup to find <script> and <meta> tags.
        """
        self.parsed_html = soup = BeautifulSoup(self.html, 'html.parser')
        self.scripts = [script['src'] for script in
                        soup.findAll('script', src=True)]
        self.meta = {
            meta['name'].lower():
                meta['content'] for meta in soup.findAll(
                    'meta', attrs=dict(name=True, content=True))
        }

    @classmethod
    def new_from_url(cls, url, verify=True):
        """
        Constructs a new WebPage object for the URL,
        using the `requests` module to fetch the HTML.

        Parameters
        ----------

        url : str
        verify: bool
        """
        if not verify:
            warnings.simplefilter('ignore', InsecureRequestWarning)
        response = requests.get(url, allow_redirects=True, verify=verify, timeout=2.5)
        return cls.new_from_response(response)

    @classmethod
    def new_from_response(cls, response):
        """
        Constructs a new WebPage object for the response,
        using the `BeautifulSoup` module to parse the HTML.

        Parameters
        ----------

        response : requests.Response object
        """
        return cls(response.url, html=response.text, headers=response.headers)


class Wappalyzer(object):
    """
    Python Wappalyzer driver.
    """
    __regex_conditional_match = re.compile(r'\\(?P<position>\d+)\?(?P<a>[\w\\]*)\:(?P<b>[\w\\]*)$')
    __regex_unconditional_match = re.compile(r'\\(?P<position>\d+)')

    def __init__(self, categories, apps):
        """
        Initialize a new Wappalyzer instance.

        Parameters
        ----------

        categories : dict
            Map of category ids to names, as in apps.json.
        apps : dict
            Map of app names to app dicts, as in apps.json.
        """
        self.categories = categories
        self.apps = apps

        for name, app in self.apps.items():
            self._prepare_app(app)

    @classmethod
    def latest(cls, apps_file=None):
        """
        Construct a Wappalyzer instance using a apps db path passed in via
        apps_file, or alternatively the default in data/apps.json
        """
        if apps_file:
            with open(apps_file, 'r') as fd:
                obj = json.load(fd)
        else:
            obj = json.loads(pkg_resources.resource_string(__name__, "data/apps.json").decode())

        return cls(categories=obj['categories'], apps=obj['apps'])

    def _prepare_app(self, app):
        """
        Normalize app data, preparing it for the detection phase.
        """

        # Ensure these keys' values are lists
        for key in ['url', 'html', 'script', 'implies']:
            try:
                value = app[key]
            except KeyError:
                app[key] = []
            else:
                if not isinstance(value, list):
                    app[key] = [value]

        # Ensure these keys exist
        for key in ['headers', 'meta']:
            try:
                value = app[key]
            except KeyError:
                app[key] = {}

        # Ensure the 'meta' key is a dict
        obj = app['meta']
        if not isinstance(obj, dict):
            app['meta'] = {'generator': obj}

        # Ensure keys are lowercase
        for key in ['headers', 'meta']:
            obj = app[key]
            app[key] = {k.lower(): v for k, v in obj.items()}

        # Prepare regular expression patterns
        for key in ['url', 'html', 'script']:
            app[key] = [self._prepare_pattern(pattern) for pattern in app[key]]

        for key in ['headers', 'meta']:
            obj = app[key]
            for name, pattern in obj.items():
                obj[name] = self._prepare_pattern(obj[name])

    def _prepare_pattern(self, pattern):
        """
        Strip out key:value pairs from the pattern and compile the regular
        expression.
        """
        regex_and_tags = pattern.split('\\;')
        regex = regex_and_tags[0]
        confidence, version = 100, None

        for tag in regex_and_tags[1:]:
            k, v = tag.split(':', 1)
            if k == 'confidence':
                confidence = int(v)
            elif k == 'version':
                version = v

        try:
            return re.compile(regex, re.I), version, confidence
        except re.error as e:
            warnings.warn(
                "Caught '{error}' compiling regex: {regex}"
                .format(error=e, regex=regex)
            )
            # regex that never matches:
            # http://stackoverflow.com/a/1845097/413622
            return re.compile(r'(?!x)x'), None, None

    def _matches(self, content, pattern):
        """
        Determine whether the pattern matches the content and return the extracted version and confidence.
        """
        regex, version, confidence = pattern
        m = regex.search(content)

        if not m:
            return None, None, 0

        def replace_cond_match(obj):
            pos = int(obj.group('position'))
            return obj.group('a') if m.group(pos) else obj.group('b')

        def replace_uncond_match(obj):
            pos = int(obj.group('position'))
            return m.group(pos)

        if version:
            version = re.sub(self.__regex_conditional_match, replace_cond_match, version)
            version = re.sub(self.__regex_unconditional_match, replace_uncond_match, version)

        return True, version, confidence

    def _has_app(self, app, webpage):
        """
        Determine whether the web page matches the app signature.
        """
        # Search the easiest things first and save the full-text search of the
        # HTML for last

        pattern_list = []

        for pattern in app['url']:
            pattern_list.append((webpage.url, pattern))

        for name, pattern in app['headers'].items():
            if name in webpage.headers:
                content = webpage.headers[name]
                pattern_list.append((content, pattern))

        for pattern in app['script']:
            for script in webpage.scripts:
                pattern_list.append((script, pattern))

        for name, pattern in app['meta'].items():
            if name in webpage.meta:
                content = webpage.meta[name]
                pattern_list.append((content, pattern))

        for pattern in app['html']:
            pattern_list.append((webpage.html, pattern))

        match, version, confidence = False, '', 0
        # Find matchings, don't stop until a version is found
        for content, pattern in pattern_list:
            pattern_match, pattern_version, pattern_confidence = self._matches(content, pattern)

            match = pattern_match if pattern_match else match
            version = pattern_version if pattern_version else version
            confidence += pattern_confidence

            if match and version and confidence >= 100:
                break

        return match, version, min(100, confidence)

    def _get_implied_apps(self, detected_apps):
        """
        Get the set of apps implied by `detected_apps`.
        """
        def __get_implied_apps(apps):
            _implied_apps = set()
            for app in apps:
                try:
                    _implied_apps.update(set(self.apps[app]['implies']))
                except KeyError:
                    pass
            return _implied_apps

        implied_apps = __get_implied_apps(detected_apps)
        all_implied_apps = set()

        # Descend recursively until we've found all implied apps
        while not all_implied_apps.issuperset(implied_apps):
            all_implied_apps.update(implied_apps)
            implied_apps = __get_implied_apps(all_implied_apps)

        return all_implied_apps

    def get_categories(self, app_name):
        """
        Returns a list of the categories for an app name.
        """
        cat_nums = self.apps.get(app_name, {}).get("cats", [])
        categories = [{int(num): self.categories[num]} for num in cat_nums]

        return categories

    def analyze(self, webpage):
        """
        Return a list of applications that can be detected on the web page.
        """
        detected_apps = []

        for app_name, app in self.apps.items():
            match, version, confidence = self._has_app(app, webpage)
            if match:
                detected_apps.append({
                    "name": app_name,
                    "version": version,
                    "confidence": confidence,
                    "categories": self.get_categories(app_name)
                })

        #detected_apps |= self._get_implied_apps(detected_apps)

        return detected_apps
