import hyperscan

import json


def process_pattern(pattern):
    pattern = pattern.split('\\;')[0]
    pattern = pattern.replace("^", "")
    if "^" in pattern and pattern[0] != "^":
        print(pattern)

    return pattern.encode()


def build_db():
    with open('data/apps.json') as fp:
        apps = json.load(fp)['apps']

    expressions, app_names = [], []
    for app, values in apps.items():
        if "html" not in values:
            continue

        html = values["html"]
        if isinstance(html, list):
            for expr in html:
                expressions.append(process_pattern(expr))
                app_names.append(app)
        else:
            expressions.append(process_pattern(html))
            app_names.append(app)

    db = hyperscan.Database()
    db.compile(expressions, flags=[hyperscan.HS_FLAG_PREFILTER for _ in range(len(expressions))])
    return db, app_names


if __name__ == '__main__':
    database = build_db()
    print(database.info())
