""" Utilities for loading and writing data. """

import csv
import json
import pickle
from collections import OrderedDict
from typing import Any

import boto3
import pandas as pd
from botocore.exceptions import NoCredentialsError
from progressbar import progressbar

from src.analysis import osrs_skills


def load_json(file: str) -> Any:
    with open(file, 'r') as f:
        return json.load(f)


def load_pkl(file: str) -> Any:
    with open(file, 'rb') as f:
        return pickle.load(f)


def dump_pkl(obj: Any, file: str):
    with open(file, 'wb') as f:
        pickle.dump(obj, f)


def import_players_csv(in_file) -> pd.DataFrame:
    return pd.read_csv(in_file, index_col='username').drop('rank', axis=1)


def export_players_csv(players_df: pd.DataFrame, out_file: str):
    players_df.insert(0, 'rank', range(1, 1 + len(players_df)))
    players_df.to_csv(out_file, header=True, index=True, index_label='username')


def export_clusterids_csv(clusterids_df: pd.DataFrame, out_file: str):
    clusterids_df.to_csv(out_file, header=True, index=True, index_label='player')


def export_centroids_csv(centroids_dict: OrderedDict[str, pd.DataFrame], out_file):
    header = ['split', 'clusterid'] + osrs_skills(include_total=False)
    with open(out_file, 'w') as f:
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


def download_from_s3(bucket: str, obj_key: str, local_file: str):
    """ Download object from an S3 bucket, writing it to a local file. """

    print(f"downloading s3://{bucket}/{obj_key}")
    s3 = boto3.client('s3')
    response = s3.head_object(Bucket=bucket, Key=obj_key)
    size = response['ContentLength']
    pbar = progressbar.ProgressBar(maxval=size)
    pbar.start()

    def update_pbar(chunk):
        pbar.update(pbar.currval + chunk)

    try:
        s3.download_file(bucket, obj_key, local_file, Callback=update_pbar)
    except FileNotFoundError:
        print("file not found")
    except NoCredentialsError:
        print("credentials not available")
