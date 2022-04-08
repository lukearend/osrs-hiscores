#!/usr/bin/env python3

""" Compute quartiles for each skill across the players in each cluster. """

import argparse
import pickle

import numpy as np
import pandas as pd
from tqdm import tqdm


def main(players_df: pd.DataFrame, clusterids: NDArray, use_skills: List[str] = None) -> pd.DataFrame:
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""Compute cluster sizes, quartiles and uniqueness.""")
    parser.add_argument('stats_file', type=str, help="load player stats from this file")
    parser.add_argument('clusterids_file', type=str, help="load player clusters from this file")
    parser.add_argument('out_file', type=str, help="write cluster quartiles to this file")
    args = parser.parse_args()

    # todo: read stats file
    # todo: read clusterids_file
    # todo: read split file and iterate through splits
    # todo: dump quartiles_file
