import hyperscan
from bs4 import BeautifulSoup

from datetime import datetime
import re
import os
import json
import logging

from pprint import pprint

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('wappalyzer')
log.setLevel(logging.DEBUG)


class Wappalyzer:
    def __init__(self, pattern_db=None, apps_path='data/apps.json'):
        if not pattern_db:
            self.engine = RePatternDatabase
        else:
            self.engine = pattern_db

        self.meta_app_keys = {}
        self.meta_expressions = {}

        self.app_keys = []
        self.expressions = []
        self.databases = {}
        self._build_db(apps_path)

    def _build_db(self, apps_path):
        with open(apps_path) as fp:
            apps = json.load(fp)['apps']

        for app, values in apps.items():
            if "html" in values:
                obj = values["html"]
                if isinstance(obj, list):
                    for expr in obj:
                        self.expressions.append(expr)
                        self.app_keys.append(app)
                else:
                    self.expressions.append(obj)
                    self.app_keys.append(app)

            if "script" in values:
                obj = values["script"]
                if isinstance(obj, list):
                    for expr in obj:
                        # TODO: make it more robust. case sensitivity, quotation marks, etc.
                        self.expressions.append("<script[^>]* src=\"{}\"".format(self._clean_inline(expr)))
                        self.app_keys.append(app)
                        #self.database = self.engine(self.expressions, self.app_keys)

            if "meta" in values:
                for key, value in values["meta"].items():
                    if not value:
                        value = ".+"
                    self.expressions.append("<meta[^>]* name=\"{}\" content=\"{}\"".format(key, self._clean_inline(value)))
                    self.app_keys.append(app)
                    #self.database = self.engine(self.expressions, self.app_keys)

        self.databases["meta"] = {}
        for key in self.meta_expressions.keys():
            self.databases["meta"][key] = self.engine(self.meta_expressions[key], self.meta_app_keys[key])

        self.database = self.engine(self.expressions, self.app_keys)

    def _clean(self, pattern):
        pattern = pattern.split('\\;')[0]
        return pattern.encode()

    def _clean_inline(self, pattern):
        pattern = pattern.split('\\;')[0]
        pattern = pattern.replace("(?:^|\s)", "\s")
        pattern = pattern[1:] if pattern[0] == "^" else pattern
        if "^" in pattern:
            print(pattern)
        return pattern.replace("$", "")

    def match(self, data):
        #scripts, meta = self._parse_html(data)
        found = self.database.match(data)

        #for script in scripts:
        #    found |= self.databases["script"].match(script)

        #for k, v in meta.items():
        #    if k in self.databases["meta"]:
        #        found |= self.databases["meta"][k].match(v)

        return found

    def _parse_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        scripts = [script['src'] for script in soup.findAll('script', src=True)]
        meta = {
            m['name'].lower(): m['content']
            for m in soup.findAll('meta', attrs=dict(name=True, content=True))
        }
        return scripts, meta


class PatternDatabase:
    def __init__(self, patterns, app_keys):
        self.patterns = patterns
        self.app_keys = app_keys

        start = datetime.now()
        self._build_db()
        logging.info('Built {} with {} patterns in {}'.format(self.__class__.__name__, len(self.patterns), datetime.now() - start))

    def _build_db(self):
        raise NotImplementedError

    def match(self, data):
        raise NotImplementedError


class HyperscanPatternDatabase(PatternDatabase):
    def _build_db(self):
        self.compiled_patterns = [re.compile(p.encode()) for p in self.patterns]
        self.db = hyperscan.Database()
        self.db.compile([p.encode() for p in self.patterns], flags=[hyperscan.HS_FLAG_PREFILTER|hyperscan.HS_FLAG_ALLOWEMPTY] * len(self.patterns))

    def match(self, data):
        results = MatchResults()
        self.db.scan(data, results)

        found = set()
        for k, match in results.matches.items():
            begin, end, _, _ = match
            if self.compiled_patterns[k].search(data[begin:end].encode()):
                found.add(self.app_keys[k])

        return found


class RePatternDatabase(PatternDatabase):
    def _build_db(self):
        self.compiled_patterns = [re.compile(self._clean(p)) for p in self.patterns]

    def match(self, data):
        return {k for p, k in zip(self.compiled_patterns, self.app_keys) if p.search(data.encode())}


class MatchResults:
    def __init__(self):
        self.matches = {}

    def __call__(self, expression_id, start, end, flags, context):
        self.matches[expression_id] = (start, end, flags, context)


if __name__ == "__main__":
    iterations = 100
    samples = []
    path = "test_html"
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            with open(os.path.join(path, file), encoding="latin-1") as fp:
                samples.append(fp.read())

    #wa = Wappalyzer(RePatternDatabase)
    wa = Wappalyzer(HyperscanPatternDatabase)

    start = datetime.now()
    for _ in range(iterations):
        for s in samples:
            wa.match(s)

    duration = datetime.now() - start
    num_checks = iterations*len(samples)

    print("Matching took: {}".format(duration))
    print("Checked {} samples => {:.2f} per second".format(num_checks, num_checks/duration.total_seconds()))
