from datetime import datetime
import os
import json
import logging

from pprint import pprint

from pattern_db import HyperscanPatternDatabase

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('wappalyzer')
log.setLevel(logging.DEBUG)


class Wappalyzer:
    def __init__(self, pattern_db=None, apps_path="../wappalyzer/data/apps.json", selected_apps=None):
        if not pattern_db:
            self.engine = HyperscanPatternDatabase
        else:
            self.engine = pattern_db

        self.active_apps = selected_apps
        self.app_keys, self.expressions, self.version_tags, self.confidence_tags = [], [], [], []
        self.header_databases = {}

        with open(apps_path) as fp:
            self.apps = json.load(fp)['apps']

        self._build_db()

    def _build_db(self):
        header_expressions, header_versions, header_confidence, header_apps = {}, {}, {}, {}
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

            if "headers" in values:
                for key, value in values["headers"].items():
                    pattern, version, confidence = self._prepare_pattern(value, True)
                    if not pattern:
                        pattern = ".*"

                    header_expressions.setdefault(key, []).append(pattern)
                    header_versions.setdefault(key, []).append(version)
                    header_confidence.setdefault(key, []).append(confidence)
                    header_apps.setdefault(key, []).append(app)

        self.database = self.engine(self.expressions, self.version_tags, self.confidence_tags, self.app_keys)

        for header in header_expressions.keys():
            self.header_databases[header] = self.engine(header_expressions[header], header_versions[header], header_confidence[header], header_apps[header])

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

    def match(self, data, headers=None, include_implied=True):
        if not headers:
            headers = {}

        found = self.database.match(data)
        for k, v in headers.items():
            if k in self.header_databases:
                # Todo: Do not overwrite old version results
                found.update(self.header_databases[k].match(v))

        if not include_implied:
            return found

        queue = set(found.keys())
        while queue:
            app = queue.pop()
            if app not in self.apps:
                continue

            if "implies" not in self.apps[app]:
                continue

            implies = self.apps[app]["implies"]
            implies = implies if isinstance(implies, list) else [implies]

            for implied_app in implies:
                implied_app, _, _ = self._prepare_pattern(implied_app, False)
                if implied_app not in found:
                    found[implied_app] = None
                    queue.add(implied_app)

        return found


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
            pprint(wa.match(s, headers={"Server": "Ubuntu"}))
            #wa.match(s)

    duration = datetime.now() - start
    num_checks = iterations*len(samples)

    print("Matching took: {}".format(duration))
    print("Checked {} samples => {:.2f} per second".format(num_checks, num_checks/duration.total_seconds()))
