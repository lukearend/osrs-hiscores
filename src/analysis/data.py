""" Utilities for loading and writing data. """

import csv
import pickle
from functools import cache
from typing import Any

import boto3
import pandas as pd
from botocore.exceptions import NoCredentialsError
from progressbar import progressbar
from tqdm import tqdm


@cache
def load_pkl(file: str) -> Any:
    with open(file, 'rb') as f:
        return pickle.load(f)


def dump_pkl(obj: Any, file: str):
    with open(file, 'wb') as f:
        pickle.dump(obj, f)


def export_players_csv(players_df: pd.DataFrame, out_file: str):
    pass


def export_centroids_csv(centroids_df: pd.DataFrame, out_file: str):
    pass


def export_clusters_csv(clusters_df: pd.DataFrame, out_file: str):
    pass


def download_from_s3(bucket: str, obj_key: str, local_file: str):
    """ Download object from an S3 bucket, writing it to a local file. """

    print(f"downloading s3://{bucket}/{obj_key}")
    s3 = boto3.client('s3')
    response = s3.head_object(Bucket=bucket, Key=obj_key)
    size = response['ContentLength']
    progress = progressbar.ProgressBar(maxval=size)
    progress.start()

    def update_progress(chunk):
        progress.update(progress.currval + chunk)

    try:
        s3.download_file(bucket, obj_key, local_file, Callback=update_progress)
    except FileNotFoundError:
        print("file not found")
    except NoCredentialsError:
        print("credentials not available")
