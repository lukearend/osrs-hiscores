""" Special data types. """

from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Tuple

import numpy as np
import pandas as pd
import xarray as xr
from numpy.typing import NDArray


@dataclass
class SplitResults:
    """ App data for one split of the dataset. """

    skills: List[str]                # length nskills in split
    cluster_quartiles: xr.DataArray  # shape (5, nclusters, nskills + 1), includes total level
    cluster_centroids: pd.DataFrame  # shape (nclusters, nskills)
    cluster_xyz: pd.DataFrame        # shape (nclusters, 3)
    cluster_sizes: NDArray           # length nclusters
    cluster_uniqueness: NDArray      # length nclusters
    xyz_axlims: Dict[str, Tuple[float, float]]


@dataclass
class PlayerResults:
    """ Stats and clustering results for a player. """

    username: str
    stats: List[int]            # includes total level
    clusterids: Dict[str, int]  # cluster ID for each split of the dataset


class PlayerRecord:
    """ Data record for one player scraped from the hiscores. """

    def __init__(self, username: str, stats: List[int], ts: datetime):
        self.username = username

        # First three stats are rank,
        self.total_level = stats[1]
        self.total_xp = stats[2]
        self.rank = stats[0]
        self.stats = np.array(stats).astype('int')
        self.ts = ts

    def __lt__(self, other):
        if self.total_level < other.total_level:
            return True
        elif self.total_level == other.total_level and self.total_xp < other.total_xp:
            return True
        elif self.total_xp == other.total_xp and self.rank > other.rank:  # worse players have higher ranks
            return True
        return False

    def __eq__(self, other):
        if other is None:
            return False
        return not self < other and not other < self

    def __ne__(self, other):
        return not self == other
    def __gt__(self, other):
        return other < self
    def __ge__(self, other):
        return not self < other
    def __le__(self, other):
        return not other < self
