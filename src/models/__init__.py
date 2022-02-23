import time

import faiss
import numpy as np
from numpy.typing import NDArray


def cluster_L2(X: NDArray, centroids: NDArray) -> NDArray:
    """
    Cluster the vectors in X according to a given list of cluster
    centroids. Each vector is assigned a cluster ID which is the
    index of the nearest centroid using the Euclidean distance.

    :param X: 2D array of vector to cluster
    :param centroids: 2D array of cluster centroids
    :return: 1D array of cluster IDs
    """
    t0 = time.time()
    index = faiss.IndexFlatL2()
    index.add(centroids)
    _, ids = index.search(X.astype('float32'), k=1)
    print(f"done ({time.time() - t0:.2f} sec)")

    ids = [i[0] for i in ids]  # index.search() returns an array of length-1 arrays
    return np.array(ids).astype('int')


def fit_kmeans(X: NDArray, k: int, w: NDArray) -> NDArray:
    """
    Determine centroids for a set of k clusters such that when each
    vector in X is assigned to the nearest cluster, the sum of distances
    between each vector and its corresponding centroid is minimized.

    :param X: 2D array of vectors to train on
    :param k: number of clusters
    :param w: 1D array of weights corresponding to vectors in X
    :return: 2D array of centroids, number of rows is k
    """
    npoints, ndims = X.shape
    kmeans = faiss.Kmeans(ndims, k, seed=0, niter=100, nredo=10,
                          verbose=True, max_points_per_centroid=npoints)
    kmeans.train(X.astype('float32'), weights=w.astype('float32'))
    return kmeans.centroids
