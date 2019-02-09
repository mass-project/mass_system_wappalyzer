import json
from traceback import format_exc


class Response:
    def __init__(self, status, headers, url, content):
        self.status = status
        self.headers = headers
        self.url = url
        self.content = content

    def __str__(self):
        return "({}, {})".format(self.status, self.url)


class Result:
    def __init__(self, url):
        self.url = url

    def serialize(self):
        raise NotImplementedError


class SuccessfulResult(Result):
    def __init__(self, url, status, matches):
        super().__init__(url)
        self.status = status
        self.matches = matches

    def serialize(self):
        return json.dumps({'status': self.status, 'url': self.url, 'matches': self.matches})


class ExceptionResult(Result):
    def __init__(self, url, exception, traceback, stage=None):
        super().__init__(url)
        self.exception = repr(exception)
        self.traceback = traceback
        self.stage = stage

    def serialize(self):
        return json.dumps({'url': self.url, 'exception': self.exception, 'traceback': self.traceback, 'stage': self.stage})
