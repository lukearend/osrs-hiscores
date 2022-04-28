""" Loading and saving data. """

import collections
import csv
import json
import pickle
import warnings
from io import BytesIO
from typing import OrderedDict, Any

import boto3
import pandas as pd
from tqdm import tqdm, TqdmWarning

from src import osrs_skills


def load_json(file: str) -> Any:
    with open(file, 'r') as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)  # preserve order


def load_pkl(file: str) -> Any:
    with open(file, 'rb') as f:
        return pickle.load(f)


def dump_pkl(obj: Any, file: str):
    with open(file, 'wb') as f:
        pickle.dump(obj, f)


def export_players_csv(players_df: pd.DataFrame, out_file: str):
    """ Write a player stats dataset to CSV file. """

    players_df.insert(0, 'rank', range(1, 1 + len(players_df)))
    with open(out_file, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['username'] + list(players_df.columns))
        for username, stats in tqdm(players_df.iterrows(), total=len(players_df)):
            line = [username]
            for n in stats:
                if n == 0:
                    line.append('')
                else:
                    line.append(n)
            writer.writerow(line)


def export_clusterids_csv(clusterids_df: pd.DataFrame, out_file: str):
    """ Write a cluster IDs dataset to CSV file. """

    clusterids_df.to_csv(out_file, header=True, index=True, index_label='player')


def export_centroids_csv(centroids_dict: OrderedDict[str, pd.DataFrame], out_file):
    """ Write centroids that results from clustering to CSV file. """

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
