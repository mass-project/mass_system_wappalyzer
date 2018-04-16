import json
import matplotlib.pyplot as plt
from collections import Counter
from datetime import datetime

if __name__ == '__main__':
    tag_a = 'Koken:0.22.24'
    tag_b = 'Koken:0.22.23'
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

    counts_ver_a = Counter(tag_appearances[tag_a])
    counts_ver_b = Counter(tag_appearances[tag_b])

    labels_a, _ = zip(*counts_ver_a.items())
    labels_b, _ = zip(*counts_ver_b.items())
    labels = sorted(list(set(labels_a) | set(labels_b)))
    values_a = [counts_ver_a[label] if label in counts_ver_a else 0 for label in labels]
    values_b = [counts_ver_b[label] if label in counts_ver_b else 0 for label in labels]

    p_a = plt.bar(range(len(values_a)), values_a)
    p_b = plt.bar(range(len(values_b)), values_b, bottom=values_a)
    plt.legend((p_a, p_b), (tag_a, tag_b))
    plt.xticks(range(len(labels)), labels, rotation=90)
    plt.show()
