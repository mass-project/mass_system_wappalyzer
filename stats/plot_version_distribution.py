import json
import matplotlib.pyplot as plt
from collections import Counter
from datetime import datetime, timedelta


def _daterange(date1, date2):
    for n in range(int((date2 - date1).days)+1):
        yield date1 + timedelta(n)


if __name__ == '__main__':
    app_name = 'WordPress'
    with open('process_report_data_results_complete.json') as fp:
        data = json.load(fp)

    tag_appearances = {}
    for sample in data:
        day = datetime.strptime(sample[0], '%Y-%m-%d %H:%M:%S').date()
        for tag in sample[1]:
            if tag in tag_appearances:
                tag_appearances[tag].append(day)
            else:
                tag_appearances[tag] = [day]

    labels = set()
    counts = {}
    for tag in tag_appearances.keys():
        if tag.startswith('{}:'.format(app_name)):
            counts[tag] = Counter(tag_appearances[tag])
            labels |= set(counts[tag].keys())

    # Add missing dates
    date_begin = min(labels)
    date_end = max(labels)
    labels = list(_daterange(date_begin, date_end))

    prev = None
    for tag, num in counts.items():
        values = [counts[tag][label] if label in counts[tag] else 0 for label in labels]
        version = tag.split(':', maxsplit=1)[1]
        plt.bar(range(len(values)), values, bottom=prev, label='{} ({})'.format(version, len(num)))
        prev = values

    plt.title(app_name)
    #plt.legend()
    plt.xticks(range(len(labels)), labels, rotation=90)
    plt.tight_layout()
    plt.show()
