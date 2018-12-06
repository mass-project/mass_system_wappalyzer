import hyperscan

import json


def process_pattern(pattern):
    pattern = pattern.split('\\;')[0]
    pattern = pattern.replace("^", "")
    if "^" in pattern and pattern[0] != "^":
        print(pattern)

    return pattern.encode()


if __name__ == '__main__':
    with open('data/apps.json') as fp:
        apps = json.load(fp)['apps']

    expressions = []
    for app, values in apps.items():
        if "html" not in values:
            continue

        html = values["html"]
        if isinstance(html, list):
            for expr in html:
                expressions.append(process_pattern(expr))
        else:
            expressions.append(process_pattern(html))

    db = hyperscan.Database()
    db.compile(expressions, flags=[hyperscan.HS_FLAG_PREFILTER for _ in range(len(expressions))])
    print(len(expressions))
