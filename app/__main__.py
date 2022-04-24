#!/usr/bin/env python3

""" Dash application to visualize clustering results for the OSRS hiscores. """

import argparse
import pickle
from typing import Dict

from pymongo.collection import Collection

from app.layout import build_layout
from app.callbacks import add_callbacks
from src.analysis.app import connect_mongo, SplitData
from src.analysis.data import load_pkl, download_s3_obj


def main(app_coll: Collection, app_data: Dict[str, SplitData], debug: bool = True):
    app = build_layout(app_data)
    app = add_callbacks(app, app_data, app_coll)
    app.run_server(debug=debug)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run main Dash application.")
    parser.add_argument('--mongo-url', required=True, help="use Mongo instance running at this URL")
    parser.add_argument('--collection', required=True, help="collection containing player data")
    parser.add_argument('--deployment', default="local", choices=['local', 'cloud'], help="deployment type")
    parser.add_argument('--data-file', help="path to main data file (for local deployment)")
    parser.add_argument('--data-bucket', help="S3 bucket containing main data file (for cloud deployment)")
    parser.add_argument('--data-s3-key', help="S3 object key for main data file (for cloud deployment)")
    parser.add_argument('--debug', action="store_true", help="if set, run in debug mode")
    args = parser.parse_args()

    player_coll = connect_mongo(args.mongo_url, args.collection)

    if args.deployment == 'cloud':
        if args.data_bucket is None:
            raise ValueError("argument '--data-bucket' is required for 'cloud' deployment")
        if args.data_s3_key is None:
            raise ValueError("argument '--data-s3-key' is required for 'cloud' deployment")
        app_data = pickle.loads(download_s3_obj(args.data_bucket, args.data_s3_key))
    else:
        if args.data_file is None:
            raise ValueError("argument '--data-file' is required for 'local' deployment")
        app_data = load_pkl(args.data_file)

    main(player_coll, app_data, args.debug)
