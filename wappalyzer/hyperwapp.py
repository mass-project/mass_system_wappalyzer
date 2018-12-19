import hyperscan

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
    def __init__(self, pattern_db=None, apps_path='data/apps.json', selected_apps=None):
        if not pattern_db:
            self.engine = HyperscanPatternDatabase
        else:
            self.engine = pattern_db

        self.active_apps = selected_apps
        self.app_keys = []
        self.expressions = []
        self.version_tags = []
        self.confidence_tags = []
        self.databases = {}

        with open(apps_path) as fp:
            self.apps = json.load(fp)['apps']

        self._build_db()

    def _build_db(self):
        for app, values in self.apps.items():
            if self.active_apps and app not in self.active_apps:
                continue

            if "html" in values:
                obj = values["html"]
                if isinstance(obj, list):
                    for expr in obj:
                        pattern, version, confidence = self._prepare_pattern(expr, False)
                        self._add_pattern(pattern, version, confidence, app)
                else:
                    pattern, version, confidence = self._prepare_pattern(obj, False)
                    self._add_pattern(pattern, version, confidence, app)

            if "script" in values:
                obj = values["script"]
                if isinstance(obj, list):
                    for expr in obj:
                        # TODO: make it more robust. case sensitivity, quotation marks, etc.
                        pattern, version, confidence = self._prepare_pattern(expr, True)
                        self._add_pattern("<script[^>]* src=\"{}\"".format(pattern), version, confidence, app)

            if "meta" in values:
                for key, value in values["meta"].items():
                    pattern, version, confidence = self._prepare_pattern(value, True)
                    if not value:
                        expr = "<meta[^>]* name=\"{}\"".format(key)
                    else:
                        expr = "<meta[^>]* name=\"{}\" content=\"{}\"".format(key, pattern)
                    self._add_pattern(expr, version, confidence, app)

        self.database = self.engine(self.expressions, self.version_tags, self.confidence_tags, self.app_keys)

    def _add_pattern(self, pattern, version, confidence, app_key):
        self.expressions.append(pattern)
        self.version_tags.append(version)
        self.confidence_tags.append(confidence)
        self.app_keys.append(app_key)

    def _prepare_pattern(self, pattern, inline):
        pattern_and_tags = pattern.split('\\;')
        pattern = pattern_and_tags[0]

        confidence, version = 100, None
        for tag in pattern_and_tags[1:]:
            k, v = tag.split(':', 1)
            if k == 'confidence':
                confidence = int(v)
            elif k == 'version':
                version = v

        if inline and pattern:
            pattern = pattern.replace("(?:^|\s)", "\s")
            pattern = pattern[1:] if pattern[0] == "^" else pattern
            pattern = pattern.replace("$", "")

        return pattern, version, confidence

    def match(self, data, include_implied=True):
        found = self.database.match(data)

        if not include_implied:
            return found

        queue = set(found.keys())
        while queue:
            app = queue.pop()
            if "implies" not in self.apps[app]:
                continue

            implies = self.apps[app]["implies"]
            implies = implies if isinstance(implies, list) else [implies]

            for implied_app in implies:
                if implied_app not in found:
                    found[implied_app] = None
                    queue.add(implied_app)

        return found


class PatternDatabase:
    def __init__(self, patterns, version_tags, confidence_tags, app_keys):
        self.patterns = patterns
        self.version_tags = version_tags
        self.confidence_tags = confidence_tags
        self.app_keys = app_keys

        start = datetime.now()
        self._build_db()
        logging.info('Built {} with {} patterns in {}'.format(self.__class__.__name__, len(self.patterns), datetime.now() - start))

    def _build_db(self):
        raise NotImplementedError

    def match(self, data):
        raise NotImplementedError


class HyperscanPatternDatabase(PatternDatabase):
    __regex_conditional_match = re.compile(r'\\(?P<position>\d+)\?(?P<a>[\w\\]*)\:(?P<b>[\w\\]*)$')
    __regex_unconditional_match = re.compile(r'\\(?P<position>\d+)'.encode())

    def _build_db(self):
        self.compiled_patterns = [re.compile(p.encode()) for p in self.patterns]
        self.db = hyperscan.Database()
        self.db.compile([p.encode() for p in self.patterns], flags=[hyperscan.HS_FLAG_PREFILTER] * len(self.patterns))

    def match(self, data):
        results = MatchResults()
        self.db.scan(data, results)

        found = {}
        for k, match in results.matches.items():
            begin, end, _, _ = match
            m = self.compiled_patterns[k].search(data[begin:end].encode())
            if not m:
                continue

            # Todo: Consider performance of this
            def replace_cond_match(obj):
                pos = int(obj.group('position'))
                return obj.group('a') if m.group(pos) else obj.group('b')

            def replace_uncond_match(obj):
                pos = int(obj.group('position'))
                return m.group(pos)

            version = self.version_tags[k]
            if version:
                version = re.sub(self.__regex_conditional_match, replace_cond_match, version)
                version = re.sub(self.__regex_unconditional_match, replace_uncond_match, version.encode())

            if version:
                found[self.app_keys[k]] = version.decode()
            elif self.app_keys[k] not in found:
                found[self.app_keys[k]] = None

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
    iterations = 1
    samples = []
    path = "test_html"
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            with open(os.path.join(path, file), encoding="latin-1") as fp:
                samples.append(fp.read())

    #wa = Wappalyzer(RePatternDatabase)
    #wa = Wappalyzer(HyperscanPatternDatabase, selected_apps={"Adminer", "WordPress", "vBulletin", "Drupal", "Disqus"})
    wa = Wappalyzer(HyperscanPatternDatabase)

    start = datetime.now()
    for _ in range(iterations):
        for s in samples:
            pprint(wa.match(s))
            #wa.match(s)

    duration = datetime.now() - start
    num_checks = iterations*len(samples)

    print("Matching took: {}".format(duration))
    print("Checked {} samples => {:.2f} per second".format(num_checks, num_checks/duration.total_seconds()))
