#!/usr/bin/env python3
import argparse
import sys

from src.common import PlayerData, playerdata_to_mongodoc, connect_mongo
from tqdm import tqdm

from src.common import line_count, load_clusterids_data, load_stats_data


def main(stats_file: str, clusters_file: str, url: str, coll_name: str, drop: bool = False):
    print(f"building collection '{coll_name}'")
    print("connecting...", end=' ', flush=True)
    db = connect_mongo(url)
    collection = db[coll_name]
    print("ok")

    nplayers = line_count(stats_file) - 1
    ndocs = collection.count_documents({})
    if not drop:
        if ndocs == nplayers:
            print("database already populated, nothing to do")
            sys.exit(0)
        if ndocs > 0:
            yesno = input("database partially populated. overwrite? [y/n] ")
            if yesno.lower() != 'y':
                print("database not modified, exiting")
                sys.exit(0)

    _, splits, clusterids = load_clusterids_data(clusters_file)
    usernames, skills, stats = load_stats_data(stats_file, include_total=True)

    if ndocs > 0:
        collection.drop()
        print("dropped existing collection")

    print("writing records...")
    batch_size = 4096
    batch = []
    for i, username in enumerate(tqdm(usernames)):
        player_stats = [int(v) for v in stats[i, :]]
        ids_per_split = {split: int(clusterids[i, j]) for j, split in enumerate(splits)}
        playerdata = PlayerData(
            username=username,
            clusterids=ids_per_split,
            stats=player_stats
        )
        doc = playerdata_to_mongodoc(playerdata)
        batch.append(doc)
        if len(batch) == batch_size:
            collection.insert_many(batch)
            batch = []
    if batch:
        collection.insert_many(batch)


if __name__ == "__main__":
    desc = """Build a collection of mappings from usernames to player info
           (stats and clustering results) in the database 'osrs-hiscores'
           at the specified Mongo instance."""

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('statsfile', type=str, help="load player stats from this CSV file")
    parser.add_argument('clustersfile', type=str, help="load player cluster IDs from this CSV file")
    parser.add_argument('-u', '--url', type=str, default="localhost:27017",
                        help="use Mongo instance running at this URL (defaults to localhost:27017)")
    parser.add_argument('-c', '--coll', type=str, default="players",
                        help="name of collection to populate (default is 'players')")
    parser.add_argument('-d', '--drop', action='store_true',
                        help="if set, will forcibly drop collection before writing (default is unset)")
    args = parser.parse_args()

    main(args.statsfile, args.clustersfile, args.url, args.coll, args.drop)
