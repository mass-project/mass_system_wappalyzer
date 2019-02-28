import numpy as np
import json

from collections import Counter
from operator import itemgetter
from matplotlib import pyplot as plt

from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
import os


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


def rate_stats(out_img_successes, out_img_requests):
    rates = np.loadtxt("rates.txt")

    # Requests
    plt.grid(True)
    plt.scatter(rates[:, 1], rates[:, 2], marker='+')
    plt.plot(rates[:, 1], moving_average(rates[:, 2], 40), color='orange')
    plt.xlabel('Number of samples')
    plt.ylabel('Completed requests per second')
    #plt.show()
    plt.savefig(out_img_requests, transparent=True)
    plt.close()

    # Success rate
    plt.grid(True)
    plt.scatter(rates[:, 1], rates[:, 5], marker='+')
    plt.plot(rates[:, 1], moving_average(rates[:, 5], 40), color='orange')
    plt.xlabel('Number of samples')
    plt.ylabel('Successful requests in percent')
    #plt.show()
    plt.savefig(out_img_successes, transparent=True)

    # Calculate rate statistics
    return {
        "requests": calculate_stats(rates[:, 2]),
        "successes": calculate_stats(rates[:, 5])
    }, int(rates[:, 1].max()), rates[:, 0].max()


def exception_stats():
    exceptions = {}
    num_exceptions = 0
    with open("exceptions.txt") as fp:
        for line in fp:
            data = json.loads(line)
            stage = data["stage"] if "stage" in data else "unknown"
            exceptions.setdefault(stage, []).append(data["exception"])
            num_exceptions +=1

    results = {}
    for k, v in exceptions.items():
        results[k] = sorted(Counter(v).items(), key=itemgetter(1), reverse=True)

    return results, num_exceptions


def result_stats():
    apps = []
    versions = {}
    num_results = 0
    with open("results.txt") as fp:
        for line in fp:
            num_results += 1
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

    return results, num_results


if __name__ == '__main__':
    date = datetime.now().strftime("%Y-%m-%d")
    out_directory = os.getenv('RESULT_DIRECTORY', os.getcwd())
    out_path_zip = os.path.join(out_directory, "{}.zip".format(date))
    out_path_agg = os.path.join(out_directory, "{}_aggregated.json".format(date))
    out_path_suc = os.path.join(out_directory, "jekyll/assets/{}_successes.png".format(date))
    out_path_req = os.path.join(out_directory, "jekyll/assets/{}_requests.png".format(date))

    rates, num_samples, seconds = rate_stats(out_path_suc, out_path_req)
    exceptions, num_exceptions = exception_stats()
    apps, num_results = result_stats()
    results = {
        "rates": rates,
        "exceptions": exceptions,
        "apps": apps,
        "run": {
            "seconds": seconds,
            "samples": num_samples,
            "avg_rate": num_samples / seconds,
            "exceptions": (num_exceptions, 100*num_exceptions/num_samples),
            "successes": (num_results, 100*num_results/num_samples)
        }
    }

    with ZipFile(out_path_zip, "w", ZIP_DEFLATED) as zip_out:
        zip_out.write("results.txt")
        zip_out.write("rates.txt")
        zip_out.write("exceptions.txt")

    with open(out_path_agg, "w") as fp:
        json.dump(results, fp)




