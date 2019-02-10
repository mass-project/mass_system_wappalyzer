import numpy as np
import json

from collections import Counter
from pprint import pprint
from matplotlib import pyplot as plt


def calculate_stats(array):
    return {
        "mean": array.mean(),
        "min": array.min(),
        "max": array.max(),
        "std": array.std(),
        "var": array.var()
    }


def moving_average(interval, window_size):
    window = np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')


def rate_stats():
    # Calculate rate statistics
    rates = np.loadtxt("rates.txt")
    stats_requests = calculate_stats(rates[:, 2])
    stats_successes = calculate_stats(rates[:, 5])

    # Requests
    plt.grid(True)
    plt.scatter(rates[:, 1], rates[:, 2], marker='+')
    plt.plot(rates[:, 1], moving_average(rates[:, 2], 40), color='orange')
    plt.xlabel('Number of samples')
    plt.ylabel('Completed requests per second')
    plt.show()

    # Success rate
    plt.grid(True)
    plt.scatter(rates[:, 1], rates[:, 5], marker='+')
    plt.plot(rates[:, 1], moving_average(rates[:, 5], 40), color='orange')
    plt.xlabel('Number of samples')
    plt.ylabel('Successful requests in percent')
    plt.show()

    pprint(stats_requests)
    pprint(stats_successes)


def exception_stats():
    exceptions = {}
    with open("exceptions.txt") as fp:
        for line in fp:
            data = json.loads(line)
            stage = data["stage"] if "stage" in data else "unknown"
            exceptions.setdefault(stage, []).append(data["exception"])

    for k, v in exceptions.items():
        print(k)
        pprint(Counter(v))


def result_stats():
    apps = []
    versions = {}
    with open("results.txt") as fp:
        for line in fp:
            for app, version in json.loads(line)["matches"].items():
                apps.append(app)
                versions.setdefault(app, []).append(version)

    app_counts = Counter(apps)
    for app, count in app_counts.most_common(30):
        print("\n\n{}: {}".format(app, count))
        pprint(Counter(versions[app]).most_common(10))


if __name__ == '__main__':
    rate_stats()
    exception_stats()
    result_stats()


