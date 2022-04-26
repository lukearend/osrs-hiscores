#!/usr/bin/env python3

""" Dash application to visualize clustering results for the OSRS hiscores. """

import argparse
import os
import pickle
import warnings
from typing import Dict

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning)  # supress dash_core_components deprecation warning
    import dash_auth

from pymongo.collection import Collection

from app.layout import build_layout
from app.callbacks import add_callbacks
from src.analysis.app import connect_mongo, SplitData
from src.analysis.data import load_pkl, download_s3_obj


def main(app_coll: Collection, app_data: Dict[str, SplitData], debug: bool = True, auth: bool = False):
    app = build_layout(app_data)
    app = add_callbacks(app, app_data, app_coll)

    if auth:
        auth_coll = connect_mongo(args.mongo_url, 'auth')
        valid_pairs = {doc['username']: doc['password'] for doc in auth_coll.find()}
        dash_auth.BasicAuth(app, valid_pairs)

    app.run_server(debug=debug)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run main Dash application.")
    parser.add_argument('--mongo-url', help="use Mongo instance running at this URL")
    parser.add_argument('--collection', help="collection containing player data")
    parser.add_argument('--deployment', default="local", choices=['local', 'cloud'], help="deployment type")
    parser.add_argument('--data-file', help="path to main data file (an S3 path for 'cloud' deployment)")
    parser.add_argument('--auth', action="store_true", help="if set, require authentication")
    parser.add_argument('--debug', action="store_true", help="if set, run in debug mode")
    args = parser.parse_args()

    for arg_name, arg_val in args.__dict__.keys():
        env_var = dict(
            mongo_url="OSRS_MONGO_URI",
            collection="OSRS_APPDATA_COLL",
            deployment="OSRS_DEPLOY_MODE",
            data_file="OSRS_APPDATA_FILE",
            auth="OSRS_ENABLE_AUTH",
            debug="OSRS_DEBUG_MODE"
        )[arg_name]
        args.__dict__[arg_name] = os.getenv(env_var, arg_val)

    player_coll = connect_mongo(args.mongo_url, args.collection)

    if args.deployment == 'cloud':
        s3_bucket, obj_key = args.data_file.replace('s3://', '').split('/', maxsplit=1)
        app_data = pickle.loads(download_s3_obj(s3_bucket, obj_key))
    else:
        app_data = load_pkl(args.data_file)

    main(player_coll, app_data, args.debug)
