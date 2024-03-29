#!/usr/bin/env python3

""" Build small dataset used for testing. """

import argparse
import numpy as np
from src.analysis.io import load_pkl, export_players_csv

parser = argparse.ArgumentParser(description="Build a small dataset for unit tests.")
parser.add_argument('--base-file', required=True, help="player stats .pkl file")
parser.add_argument('--out-file', required=True, help="write small dataset to this CSV file")
args = parser.parse_args()

players = load_pkl(args.in_file)
players = players.sample(10000, random_state=0)

sortinds = np.argsort(players['total'])[::-1]
players = players.iloc[sortinds]

export_players_csv(players, args.out_file)
print("built test data")
