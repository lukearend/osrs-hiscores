""" Condense raw stats file from scraping into a clean skills dataset. """

import csv

from tqdm import tqdm

from src import osrs_skills, count_csv_rows
from src.scrape import csv_to_player, csv_api_stats


def main(in_file: str, out_file: str):
    print("reading input file...")
    with open(in_file, 'r') as f:
        _ = f.readline()  # skip header
        players = []
        for line in tqdm(f.readlines(), total=count_csv_rows(in_file, header=True)):
            players.append(csv_to_player(line.strip()))

    # Sort accounts from best to worst and reassign ranks.
    players = sorted(players)
    for i, player in enumerate(players, start=1):
        player.rank = i
    print("sorted players")

    print("writing output file...")
    with open(out_file, 'w') as f:
        writer = csv.writer(f)
        header = ['username', 'rank'] + osrs_skills(include_total=True)
        writer.writerow(header)

        stat_inds = [csv_api_stats().index(s + '_level') for s in osrs_skills(include_total=True)]
        for i, p in tqdm(enumerate(players)):
            player_skills = [p.stats[i] for i in stat_inds]
            player_csv = [p.username, p.rank] + [str(i) for i in player_skills]
            writer.writerow(player_csv)


if __name__ == '__main__':
    infile = '/Users/lukearend/projects/osrs-hiscores/data/raw/player-stats-raw.tmp'
    outfile = '/Users/lukearend/projects/osrs-hiscores/data/raw/player-stats.csv'
    main(infile, outfile)
