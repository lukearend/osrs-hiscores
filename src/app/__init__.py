from collections import defaultdict
from typing import List, Dict

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm


# todo: make this compute for one split instead, loop over splits in main() of calling script
def compute_cluster_sizes(cluster_ids: NDArray, splitnames: List[str]) -> Dict[str, NDArray]:
    assert len(splitnames) == cluster_ids.shape[1]

    cluster_sizes = {split: defaultdict(int) for split in splitnames}
    for player_cids in tqdm(cluster_ids):
        for split, cid in zip(splitnames, player_cids):
            cluster_sizes[split][cid] += 1

    for split, sizes_dict in cluster_sizes.items():
        nclusters = max(sizes_dict.keys()) + 1
        sizes_array = np.zeros(nclusters, dtype='int')
        for cluster_id, size in sizes_dict.items():
            sizes_array[cluster_id] = size
        cluster_sizes[split] = sizes_array

    return cluster_sizes
