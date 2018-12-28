import hyperscan
import logging
import re
from datetime import datetime


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
    __regex_unconditional_match = re.compile(r'\\(?P<position>\d+)')

    def _build_db(self):
        self.compiled_patterns = [re.compile(p) for p in self.patterns]
        self.db = hyperscan.Database()
        self.db.compile([p.encode() for p in self.patterns], flags=[hyperscan.HS_FLAG_PREFILTER|hyperscan.HS_FLAG_ALLOWEMPTY] * len(self.patterns))

    def match(self, data):
        results = MatchResults()
        self.db.scan(data, results)

        found = {}
        for k, match in results.matches.items():
            begin, end, _, _ = match
            m = self.compiled_patterns[k].search(data[begin:end])
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
                version = re.sub(self.__regex_unconditional_match, replace_uncond_match, version)

            if version:
                found[self.app_keys[k]] = version
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
