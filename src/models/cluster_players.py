""" Segment OSRS playerbase into clusters of a fixed minimum distance from
    one another in the L1 metric space. Accounts are represented as length-23
    vectors of the level in each skill, and can be compared by vector
    subtraction. The distance between two players is proportional to the
    sum of their stat-by-stat differences. Players exceeding a fixed
    distance threshold from one another are allocated separate clusters.
"""

import csv
import math
import pathlib
import sys

import numpy as np
from tqdm import tqdm

from boonnano import NanoHandle


def main(stats_file, out_file):
    print("clustering player stats...")

    print("reading stats data...")
    with open(stats_file, 'r') as f:
        usernames = []
        stats_list = []
        reader = csv.reader(f)
        _ = next(reader)            # Discard header
        for line in tqdm(reader):
            username = line[0]
            player_levels = [int(n) for n in line[5::3]]
            usernames.append(username)
            stats_list.append(player_levels)

    print("building data array...")
    usernames = np.array(usernames)
    stats = np.array(stats_list, dtype='int')
    del stats_list

    # Replace missing data with 1s. This is an alright assumption for
    # for clustering purposes because unranked stats are generally low.
    stats[np.where(stats == -1)] = 1
    splits = ['all', 'cb', 'noncb']

    # Get clustering model instance.
    nano = NanoHandle(timeout=None)
    success, response = nano.open_nano('0')
    if not success:
        raise ValueError(response)

    results = {}
    for split in splits:

        # Split the dataset by all, combat-only, and non-combat only skillsets,
        # and set clustering parameters based on the current split.
        if split == 'all':
            dataset = stats
        elif split == 'cb':
            dataset = stats[:, :7]
        elif split == 'noncb':
            dataset = stats[:, 7:]

        # Set clustering parameters based on split of the dataset.
        num_features = dataset.shape[1]
        mins = num_features * [1]
        maxes = num_features * [99]
        weights = num_features * [1]
        if split == 'all':
            # The 7 combat skills exhibit considerably less variation than
            # other 16 non-combat skills. Combat vs. non-combat skills are
            # weighted 2:1 to balance their influence on clustering.
            weights = 7 * [2 * 16] + 16 * [7]
        pv = {
            'all'   : 0.103,
            'cb'    : 0.039,
            'noncb' : 0.123
        }[split]

        success, response = nano.configure_nano(feature_count=num_features,
                                                min_val=mins, max_val=maxes, weight=weights,
                                                percent_variation=pv, autotune_range=False)
        if not success:
            raise ValueError(response)

        # Inference the data in batches.
        print("clustering split '{}'...".format(split))
        cluster_ids = np.zeros(len(dataset), dtype='int')
        batch_size = 10000
        done = False
        end_i = 0
        with tqdm(total=math.ceil(len(dataset) / batch_size)) as pbar:
            while not done:
                start_i = end_i
                end_i = start_i + batch_size
                if end_i >= len(cluster_ids):
                    end_i = len(cluster_ids)
                    done = True
                batch = dataset[start_i:end_i]

                success, response = nano.load_data(batch)
                if not success:
                    raise ValueError(response)

                success, response = nano.run_nano(results='ID')
                if not success:
                    raise ValueError(response)

                cluster_ids[start_i:end_i] = response['ID']
                pbar.update(1)

        print("split: {}, pv: {}, num clusters: {}".format(split, pv, max(cluster_ids)))
        results[split] = cluster_ids

    print("writing cluster IDs to CSV...")
    with open(out_file, 'w') as f:
        f.write('username,{}\n'.format(','.join(splits)))
        for i, username in tqdm(enumerate(usernames)):
            player_ids = ','.join([str(results[split][i]) for split in splits])
            f.write("{},{}\n".format(username, player_ids))

    print("done")


if __name__ == '__main__':
    main(*sys.argv[1:])
