import json
from pprint import pprint


def read_output_file(fp):
    results = {}
    for line in fp.readlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            print('Failed: {}'.format(line))
            raise

        if not data["urls"]:
            continue

        url = data["urls"][0].replace('/', '').replace('https:', '')
        results[url] = data["applications"]
    return results


def get_app_dict(apps):
    return {app['name']: app['version'] for app in apps if int(app['confidence']) == 100}


if __name__ == '__main__':
    with open('output_native.txt') as fp:
        results_native = read_output_file(fp)

    with open('output_node.txt') as fp:
        results_node = read_output_file(fp)

    url_not_in_native, url_not_in_node, app_not_in_native, app_not_in_node = set(), set(), {}, {}
    for url, apps_node in results_node.items():
        if not apps_node:
            if url in results_native: url_not_in_node.add(url)
            continue
        if url not in results_native:
            url_not_in_native.add(url)
            continue
        apps_native = results_native[url]
        native_dict = get_app_dict(apps_native)
        node_dict = get_app_dict(apps_node)

        apps = set(node_dict.keys()) | set(native_dict.keys())
        for app_name in apps:
            if app_name not in node_dict:
                app_not_in_node[app_name] = app_not_in_node.get(app_name, 0) + 1
                continue
            if app_name not in native_dict:
                app_not_in_native[app_name] = app_not_in_native.get(app_name, 0) + 1
                continue

    print('App not in native:')
    pprint(sorted( ((v, k) for k, v in app_not_in_native.items()), reverse=True))

    print('\n\nApp not in node:')
    pprint(sorted( ((v, k) for k, v in app_not_in_node.items()), reverse=True))

    print('\n\nURL not in native ({}):'.format(len(url_not_in_native)))
    print('-'*20)
    #pprint(not_in_native)

    print('\n\nURL not in node ({}):'.format(len(url_not_in_node)))
    print('-' * 20)
    #pprint(not_in_node)