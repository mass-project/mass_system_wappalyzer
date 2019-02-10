import numpy as np
import json

from collections import Counter
from operator import itemgetter
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
    rates = np.loadtxt("rates.txt")

    # Requests
    plt.grid(True)
    plt.scatter(rates[:, 1], rates[:, 2], marker='+')
    plt.plot(rates[:, 1], moving_average(rates[:, 2], 40), color='orange')
    plt.xlabel('Number of samples')
    plt.ylabel('Completed requests per second')
    #plt.show()
    plt.savefig('requests.png')
    plt.close()

    # Success rate
    plt.grid(True)
    plt.scatter(rates[:, 1], rates[:, 5], marker='+')
    plt.plot(rates[:, 1], moving_average(rates[:, 5], 40), color='orange')
    plt.xlabel('Number of samples')
    plt.ylabel('Successful requests in percent')
    #plt.show()
    plt.savefig('successes.png')

    # Calculate rate statistics
    return {
        "requests": calculate_stats(rates[:, 2]),
        "successes": calculate_stats(rates[:, 5])
    }


def exception_stats():
    exceptions = {}
    with open("exceptions.txt") as fp:
        for line in fp:
            data = json.loads(line)
            stage = data["stage"] if "stage" in data else "unknown"
            exceptions.setdefault(stage, []).append(data["exception"])

    results = {}
    for k, v in exceptions.items():
        results[k] = sorted(Counter(v).items(), key=itemgetter(1), reverse=True)

    return results


def result_stats():
    apps = []
    versions = {}
    with open("results.txt") as fp:
        for line in fp:
            for app, version in json.loads(line)["matches"].items():
                apps.append(app)
                versions.setdefault(app, []).append(version)

    results = []
    app_counts = Counter(apps)
    for app, count in sorted(app_counts.items(), key=itemgetter(1), reverse=True):
        results.append({
            "app": app,
            "count": count,
            "versions": sorted(Counter(versions[app]).items(), key=itemgetter(1), reverse=True)
        })

    return results


if __name__ == '__main__':
    results = {
        "rates": rate_stats(),
        "exceptions": exception_stats(),
        "apps": result_stats()
    }

    with open("aggregated.json", "w") as fp:
        json.dump(results, fp)




