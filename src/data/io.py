""" Loading and saving data. """

import collections
import csv
import json
import pickle
import warnings
from io import BytesIO
from typing import OrderedDict, Any, Dict

import boto3
import numpy as np
import pandas as pd
from tqdm import tqdm, TqdmWarning

from src.common import osrs_skills
from src.data.types import SplitResults


def load_json(file: str) -> Any:
    with open(file, 'r') as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)  # preserve order


def load_pkl(file: str) -> Any:
    with open(file, 'rb') as f:
        return pickle.load(f)


def dump_pkl(obj: Any, file: str):
    with open(file, 'wb') as f:
        pickle.dump(obj, f)


def import_players_csv(file: str) -> pd.DataFrame:
    """ Read player stats dataset from a CSV file. """

    stats_df = pd.read_csv(file, index_col='username')
    stats_df.drop('rank', axis=1, inplace=True)
    stats_df[np.isnan(stats_df)] = 1
    return stats_df.astype('uint16')


def import_clusterids_csv(file: str) -> pd.DataFrame:
    """ Read cluster IDs dataset from a CSV file. """

    return pd.read_csv(file, index_col='player').astype('int')


def import_centroids_csv(file: str) -> OrderedDict[str, pd.DataFrame]:
    """ Read cluster centroids from a CSV file. """

    raw_df = pd.read_csv(file)

    k_per_split = collections.OrderedDict()
    last_split = None
    for split in raw_df['split']:
        if split != last_split:
            k_per_split[split] = 1
            last_split = split
        else:
            k_per_split[split] += 1

    centroids_per_split = collections.OrderedDict()
    cursor = 0
    for split, nclusters in k_per_split.items():
        split_df = raw_df.iloc[cursor:cursor + nclusters]
        centroids = split_df.drop('split', axis=1)
        centroids.set_index('clusterid', drop=True, inplace=True)
        centroids.dropna(axis=1, inplace=True)
        centroids_per_split[split] = centroids
        cursor += nclusters

    return centroids_per_split


def export_players_csv(players_df: pd.DataFrame, file: str):
    """ Write a player stats dataset to CSV file. """

    print("writing player stats to CSV...")
    with open(file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['username', 'rank'] + list(players_df.columns))
        for rank, (uname, stats) in tqdm(enumerate(players_df.iterrows(), 1), total=len(players_df)):
            line = [uname, rank]
            for n in stats:
                if n == 0:
                    line.append('')
                else:
                    line.append(n)
            writer.writerow(line)


def export_clusterids_csv(clusterids_df: pd.DataFrame, file: str):
    """ Write a cluster IDs dataset to CSV file. """

    clusterids_df.to_csv(file, header=True, index=True, index_label='player')


def export_centroids_csv(centroids_dict: OrderedDict[str, pd.DataFrame], file):
    """ Write centroids that results from clustering to CSV file. """

    header = ['split', 'clusterid'] + osrs_skills(include_total=False)
    with open(file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for split, split_centroids in centroids_dict.items():
            lines = []
            for clusterid, centroid in split_centroids.iterrows():
                skill_vals = []
                for s in osrs_skills():
                    skill_vals.append('' if s not in centroid.index else centroid[s])
                lines.append([split, clusterid] + skill_vals)
            writer.writerows(lines)


def download_s3_obj(bucket: str, obj_key: str) -> bytes:
    """ Download raw object from an S3 bucket with progress bar. """

    warnings.filterwarnings("ignore", category=TqdmWarning)  # supress warning from float iteration

    s3 = boto3.client('s3')
    response = s3.head_object(Bucket=bucket, Key=obj_key)
    size = response['ContentLength']

    print(f"downloading s3://{bucket}/{obj_key}")
    f = BytesIO()
    with tqdm(total=size, unit='B', unit_scale=True) as pbar:
        s3.download_fileobj(bucket, obj_key, f,
                            Callback=lambda n: pbar.update(n))

    f.seek(0)  # put cursor back at beginning of file
    return f.read()


def load_app_data(path) -> OrderedDict[str, SplitResults]:
    """ Load app data from S3 bucket or local path. """

    if path.startswith('s3://'):
        s3_bucket, obj_key = path.replace('s3://', '').split('/', maxsplit=1)
        app_data = pickle.loads(download_s3_obj(s3_bucket, obj_key))
    else:
        app_data = load_pkl(path)

    msg = 'invalid app data'
    assert isinstance(app_data, OrderedDict), msg
    for split, data in app_data.items():
        assert isinstance(split, str) and isinstance(data, SplitResults), msg

    return app_data
