""" Code for building app dependencies. """

from dataclasses import dataclass
from typing import List, OrderedDict

import pandas as pd
from numpy.typing import NDArray
from pymongo.collection import Collection


@dataclass
class SplitData:
    """ Contains app data for one split of the dataset. """

    skills: List[str]
    cluster_centroids: NDArray
    cluster_sizes: NDArray
    cluster_quartiles: NDArray
    cluster_uniqueness: NDArray
    cluster_xyz: NDArray
    xyz_axlims: NDArray


def build_appdata_obj(centroids_df, xyz_df, quartiles_df, clusterids_df) -> OrderedDict[str, SplitData]:
    pass


def populate_collection(players_df: pd.DataFrame, clusterids_df: pd.DataFrame, collection: Collection):
    pass
