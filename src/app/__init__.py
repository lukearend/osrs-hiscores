from dataclasses import dataclass
from typing import Dict, List

from numpy.typing import NDArray

from src import DatasetSplit


@dataclass
class ClusterData:
    """ Contains app data for a set of clusters. """
    xyz: Dict  # TODO: becomes NDArray once umap params frozen
    sizes: NDArray
    centroids: NDArray
    quartiles: NDArray
    uniqueness: NDArray


@dataclass
class SplitData:
    """ Contains app data for one split of the dataset. """
    skills: List[str]
    clusterdata: ClusterData
    axlims: Dict  # TODO: becomes Dict[NDArray] once umap params frozen


@dataclass
class AppData:
    """ Contains all data needed to run Dash app. """
    splitnames: List[DatasetSplit]
    splitdata: Dict[str, SplitData]