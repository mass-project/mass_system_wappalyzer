
class Response:
    def __init__(self, status, headers, url, content):
        self.status = status
        self.headers = headers
        self.url = url
        self.content = content

    def __str__(self):
        return "({}, {})".format(self.status, self.url)
