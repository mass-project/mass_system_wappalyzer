from build_hs_db import build_db

from datetime import datetime
import os


class MatchHandler:
    def __init__(self, app_keys):
        self.matches = set()
        self.app_keys = app_keys

    def __call__(self, expression_id, start, end, flags, context):
        self.matches.add(self.app_keys[expression_id])


if __name__ == "__main__":
    iterations = 100000
    samples = []
    path = "test_html"
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            with open(os.path.join(path, file), encoding="latin-1") as fp:
                samples.append(fp.read())

    start = datetime.now()
    db, app_keys = build_db()
    print("Building DB of {} patterns took: {}".format(len(app_keys), datetime.now() - start))

    start = datetime.now()
    for _ in range(iterations):
        handler = MatchHandler(app_keys)
        for s in samples:
            db.scan(s, handler)
    duration = datetime.now() - start
    num_checks = iterations*len(samples)

    print("Matching took: {}".format(duration))
    print("Checked {} samples => {:.2f} per second".format(num_checks, num_checks/duration.total_seconds()))
