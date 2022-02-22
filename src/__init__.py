import csv
from collections import defaultdict
from subprocess import check_output

import boto3
import numpy as np
import progressbar as progressbar
from botocore.exceptions import NoCredentialsError
from tqdm import tqdm


def line_count(file):
    return int(check_output(['wc', '-l', file]).split()[0])


def load_stats_data(file):
    print("loading stats data...")
    num_players = line_count(file) - 1
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)               # Discard header

        skills = []
        for field in header[2::3]:
            skills.append(field[:-len('_level')])

        usernames = np.zeros(num_players, dtype='<U12')
        stats = np.zeros((num_players, len(skills)), dtype='int')
        for i in tqdm(range(num_players)):
            line = next(reader)
            usernames[i] = line[0]
            stats[i, :] = line[2::3]    # Just take skill level (not rank, xp)

    return usernames, skills, stats

def load_centroid_data(file):
    print("loading centroids data...")
    num_records = line_count(file) - 1
    with open(file, 'r') as f:
        reader = csv.reader(f)

        header = next(reader)
        skills = header[2:]  # drop split, cluster ID columns

        clusters_per_split = defaultdict(int)
        splits = np.zeros(num_records, dtype='str')
        ids = np.zeros(num_records)
        all_centroids = np.zeros((num_records, len(skills)))
        for i in tqdm(range(num_records)):
            line = next(reader)
            split = line[0]
            splits[i] = split
            ids[i] = line[1]
            all_centroids[i, :] = line[2:]
            clusters_per_split[split] += 1

    print("rearranging into map...", end=' ', flush=True)
    centroids = {}
    for split in set(splits):
        centroids[split] = np.zeros((clusters_per_split[split], len(skills)))
    for split, id, centroid in zip(splits, ids, all_centroids):
        centroids[split][id, :] = centroid
    print("done")

    return centroids


def load_cluster_data(file):
    print("loading cluster data...")
    num_players = line_count(file) - 1
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        splits = header[1:]

        usernames = np.zeros(num_players, dtype='<U12')
        cluster_ids = np.zeros((num_players, len(splits)), dtype='int')
        for i in tqdm(range(num_players)):
            line = next(reader)
            usernames[i] = line[0]
            cluster_ids[i, :] = line[1:]

    return usernames, splits, cluster_ids


def download_from_s3(bucket, s3_file, local_file):
    print(f"downloading s3://{bucket}/{s3_file}")
    s3 = boto3.client('s3')
    response = s3.head_object(Bucket=bucket, Key=s3_file)
    size = response['ContentLength']
    progress = progressbar.progressbar.ProgressBar(maxval=size)
    progress.start()

    def update_progress(chunk):
        progress.update(progress.currval + chunk)

    try:
        s3.download_file(bucket, s3_file, local_file, Callback=update_progress)
    except FileNotFoundError:
        print(f"file not found")
    except NoCredentialsError:
        print(f"credentials not available")
