""" Condense raw stats file from scraping into a clean skills dataset. """

import csv
import shlex
import subprocess

from tqdm import tqdm

from src.common import osrs_skills
from src.scrape import csv_to_player, csv_api_stats


def main(in_file: str, out_file: str):
    print("reading raw scrape file...")
    stdout = subprocess.check_output(shlex.split(f"wc -l {in_file}"))  # count lines in file
    nlines = int(stdout.decode().strip().split()[0])  # stdout returns both line count and filename
    with open(in_file, 'r') as f:
        _ = f.readline()  # discard header
        players = []
        for line in tqdm(f.readlines(), total=nlines - 1):
            players.append(csv_to_player(line.strip()))

    # Deduplicate any records with matching usernames by taking the later one.
    print("cleaning...")
    seen = {}
    for record in players:
        if record.username not in seen.keys():
            seen[record.username] = record
        else:
            existing_record = seen[record.username]
            seen[record.username] = record if record.ts > existing_record.ts else existing_record

    # Sort accounts from best to worst and reassign ranks.
    players = sorted(players, reverse=True)
    for i, player in enumerate(players, start=1):
        player.rank = i

    print("writing cleaned up stats file...")
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
    infile = '/Users/lukearend/projects/osrs-hiscores/data/raw/player-stats-raw.csv'
    outfile = '/Users/lukearend/projects/osrs-hiscores/data/raw/player-stats.csv'
    main(infile, outfile)
