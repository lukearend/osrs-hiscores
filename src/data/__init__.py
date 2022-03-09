def load_stats_csv(file: str):


def unpickle(file):


def load_player_stats():
    pass







def load_stats_data(file: str, include_total=True) -> Tuple[List[str], List[str], NDArray]:
    """
    Load dataset of player skill levels. Each row of the dataset is a vector of
    skill levels for a player with the columns corresponding to total level and
    the 23 OSRS skills. Level values are integers between 1 and 99, with -1
    indicating data that is missing due to the player being unranked in a skill.

    :param file: load data from this CSV file
    :param include_total: whether to include total level column
    :return:
      - list of player usernames
      - list of OSRS stat names
      - 2D array of player stat vectors
    """
    print("loading player stats data...")
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)

        statnames = []
        for field in header[2::3]:
            statnames.append(field[:-len('_level')])

        nplayers = line_count(file) - 1
        usernames = []
        stats = np.zeros((nplayers, len(statnames)), dtype='int')
        with tqdm(total=nplayers) as pbar:
            for i, line in enumerate(reader):
                usernames.append(line[0])
                stats[i, :] = [int(i) for i in line[2::3]]  # take levels, drop rank and xp columns
                pbar.update(1)

        if not include_total:
            total_ind = statnames.index("total")
            stats = np.delete(stats, total_ind, axis=1)
            del statnames[total_ind]

    return usernames, statnames, stats


def load_centroid_data(file: str) -> Dict[str, NDArray]:
    """
    Load dataset of cluster centroids resulting from the clustering runs on
    each split of the data. Each centroid is a vector is "OSRS skill" space
    representing the center of a cluster of similar accounts.

    :param file: load centroids from this CSV file
    :return: 2D array where row N is the centroid for cluster N
    """
    with open(file, 'r') as f:
        reader = csv.reader(f)
        next(reader)  # discard header

        clusterids = defaultdict(list)
        centroids = defaultdict(list)
        for i, line in enumerate(reader):
            splitname = line[0]
            clusterid = int(line[1])
            centroid = [float(v) for v in line[2:] if v != '']
            clusterids[splitname].append(clusterid)
            centroids[splitname].append(centroid)

    splits = load_splits()
    centroids_per_split = {}
    for split in splits:
        split_centroids = np.zeros_like(centroids[split.name])
        for i, cid in enumerate(clusterids[split.name]):
            split_centroids[cid, :] = centroids[split.name][i]
        centroids_per_split[split.name] = split_centroids
    return centroids_per_split


def load_clusterids_data(file: str) -> Tuple[List[str], List[str], NDArray]:
    """
    Load dataset of cluster IDs for each player. Each player is assigned a
    cluster ID for each data split; ie, cluster IDs differ for a player
    when clustering is run on different subsets of account stats.

    :param file: load player cluster IDs from this CSV file
    :return:
      - list of player usernames
      - list of split names
      - 2D array where each row is the cluster IDs for a player
    """
    print("loading cluster IDs...")
    nplayers = line_count(file) - 1
    with open(file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        splits = header[1:]

        usernames = []
        cluster_ids = np.zeros((nplayers, len(splits)), dtype='int')
        for i in tqdm(range(nplayers)):
            line = next(reader)
            usernames.append(line[0])
            cluster_ids[i, :] = line[1:]

    return usernames, splits, cluster_ids
