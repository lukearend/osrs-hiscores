import argparse
import pickle
from typing import Any

from src.data import PlayerStatsDataset
from src.data import load_stats_data_csv


def main(stats_csv_file: str, stats_pkl_file: str) -> Any:
    data: PlayerStatsDataset = load_stats_data_csv(stats_csv_file, include_total=True)
    with open(stats_pkl_file, 'wb') as f:
        pickle.dump(data, f)


if __name__ == '__main__':
    desc = """Read player stats data from a CSV file and serialize it to a .pkl."""
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('in_file', metavar='infile', type=str,
                        help="load player data from this CSV file")
    parser.add_argument('out_file', metavar='outfile', type=str,
                        help="dump player data to this .pkl file")

    args = parser.parse_args()
    main(args.infile, args.outfile)
