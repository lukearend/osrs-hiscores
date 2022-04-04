from dataclasses import dataclass
from typing import Dict, List

from numpy.typing import NDArray

from src import DatasetSplit


@dataclass
class ClusterData:
    """ Contains app data for a set of clusters. """

    xyz: NDArray
    sizes: NDArray
    centroids: NDArray
    quartiles: NDArray
    uniqueness: NDArray


@dataclass
class SplitData:
    """ Contains app data for one split of the dataset. """

    skills: List[str]
    clusterdata: ClusterData
    axlims: NDArray


@dataclass
class AppData:
    """ Contains all data needed to run Dash app. """

    splitnames: List[DatasetSplit]
    splitdata: Dict[str, SplitData]


@dataclass
class BoxplotLayout:
    """ Contains layout information for rendering boxplot for a specific split. """
    ticklabels: List[str]
    tickxoffset: float
