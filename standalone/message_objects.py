
class Response:
    def __init__(self, status, headers, url, content):
        self.status = status
        self.headers = headers
        self.url = url
        self.content = content

        #print("Created Response", status, url, headers)
