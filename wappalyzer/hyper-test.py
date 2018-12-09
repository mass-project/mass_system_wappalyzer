import hyperscan
from bs4 import BeautifulSoup

from datetime import datetime
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('wappalyzer')
log.setLevel(logging.DEBUG)


class Wappalyzer:
    def __init__(self, apps_path='data/apps.json'):
        self.meta_app_keys = {}
        self.meta_expressions = {}

        self.categories = ["html", "script"]
        self.app_keys = {k: [] for k in self.categories}
        self.expressions = {k: [] for k in self.categories}
        self.databases = {}
        self._build_db(apps_path)

    def _build_db(self, apps_path):
        with open(apps_path) as fp:
            apps = json.load(fp)['apps']

        for app, values in apps.items():
            for cat in self.categories:
                if cat in values:
                    obj = values[cat]
                    if isinstance(obj, list):
                        for expr in obj:
                            self.expressions[cat].append(expr)
                            self.app_keys[cat].append(app)
                    else:
                        self.expressions[cat].append(obj)
                        self.app_keys[cat].append(app)

            if "meta" in values:
                for key, value in values["meta"].items():
                    if not value:
                        # Todo: Match empty meta headers
                        continue
                    self.meta_expressions.setdefault(key, []).append(value)
                    self.meta_app_keys.setdefault(key, []).append(app)

        self.databases["meta"] = {}
        for key in self.meta_expressions.keys():
            self.databases["meta"][key] = PatternDatabase(self.meta_expressions[key], self.meta_app_keys[key])

        for cat in self.categories:
            self.databases[cat] = PatternDatabase(self.expressions[cat], self.app_keys[cat])

    def match(self, data):
        scripts, meta = self._parse_html(data)
        found = self.databases["html"].match(data)

        for script in scripts:
            found |= self.databases["script"].match(script)

        for k, v in meta.items():
            if k in self.databases["meta"]:
                found |= self.databases["meta"][k].match(v)

        print(found)
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
        logging.info('Built PatternDB with {} patterns in {}'.format(len(self.patterns), datetime.now() - start))

    def _build_db(self):
        self.db = hyperscan.Database()
        self.db.compile([self._clean(p) for p in self.patterns], flags=[hyperscan.HS_FLAG_PREFILTER|hyperscan.HS_FLAG_ALLOWEMPTY] * len(self.patterns))

    @staticmethod
    def _clean(pattern):
        pattern = pattern.split('\\;')[0]
        pattern = pattern.replace("^", "")
        if "^" in pattern and pattern[0] != "^":
            print(pattern)

        return pattern.encode()

    def match(self, data):
        results = MatchResults()
        self.db.scan(data, results)
        return {self.app_keys[k] for k in results.matches.keys()}


class MatchResults:
    def __init__(self):
        self.matches = {}

    def __call__(self, expression_id, start, end, flags, context):
        self.matches[expression_id] = (start, end, flags, context)


if __name__ == "__main__":
    iterations = 1
    samples = []
    path = "test_html"
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            with open(os.path.join(path, file), encoding="latin-1") as fp:
                samples.append(fp.read())

    wa = Wappalyzer()

    start = datetime.now()
    for _ in range(iterations):
        for s in samples:
            wa.match(s)

    duration = datetime.now() - start
    num_checks = iterations*len(samples)

    print("Matching took: {}".format(duration))
    print("Checked {} samples => {:.2f} per second".format(num_checks, num_checks/duration.total_seconds()))
