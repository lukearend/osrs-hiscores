from dataclasses import dataclass
from typing import List

from numpy.typing import NDArray


@dataclass
class PlayerStatsData:
    """
    A dataset of OSRS account skill levels.

    :usernames: usernames in dataset (correspond to rows)
    :skills: skills in dataset (correspond to columns)
    :levels: 2D array where each row gives a player's levels in each skill
    """
    usernames: List[str]  # usernames in dataset (correspond to rows)
    skills: List[str]     # skills in dataset (correspond to columns)
    levels: NDArray       # 2D array where each row gives a player's levels in each skill


@dataclass
class PlayerClustersData:
    """
    The results of clustering runs on the OSRS account data set.

    :usernames: usernames in dataset (correspond to rows)
    :splits: the different data splits for which clustering was run (correspond to columns)
    :clusterids: 2D array where each row gives a player's assigned cluster ID for each split
    """
    usernames: List[str]
    splits: List[str]
    clusterids: NDArray


@dataclass
class ClusterCentroids:
    """
    Centroids for a set of clusters in OSR account space.

    :clusterids: cluster IDs corresponding to rows of centroid array
    :skills: skills corresponding to columns of centroid array
    :centroids: 2D array where each row is the centroid of a cluster in OSRS account space

    """
    clusterids: List[int]
    skills: List[str]
    centroids: NDArray


@dataclass
class ClusterAnalytics:
    """
    Analytics for a set of clusters.

    :sizes: array where element N is the number of players in cluster N
    :quartiles: 3D array where page N is a 5 x nskills array containing quartiles
        0, 25, 50, 75 and 100 for each stat, aggregated over the players in cluster N
    :uniqueness: array where element N is the uniqueness score for accounts in cluster N
    """
    sizes: NDArray
    quartiles: NDArray
    uniqueness: NDArray
