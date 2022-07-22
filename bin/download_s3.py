#!/usr/bin/env python3

""" Download an S3 object to a local file. """

import argparse
import os
import sys
from src.common import download_s3_obj

parser = argparse.ArgumentParser(description="Download an S3 object to a local file.")
parser.add_argument('s3_url', help="S3 URL for object to download")
parser.add_argument('out_file', help="write object to this file as a binary blob")
args = parser.parse_args()

if os.path.isfile(args.out_file):
    print(f"{args.out_file} already exists, skipping download")
    sys.exit(0)

blob = download_s3_obj(url=args.s3_url)
with open(args.out_file, 'wb') as f:
    f.write(blob)

print(f"wrote to {args.out_file}")
