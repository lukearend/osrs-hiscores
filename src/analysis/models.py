""" Core machine learning models. """

import os
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)  # suppress warning about distutils Version classes
    import faiss
import numpy as np
import umap
from numpy.typing import NDArray

os.environ["KMP_WARNINGS"] = 'off'  # suppress OMP deprecation warning from UMAP (github.com/numba/numba/issues/5275)


def fit_kmeans(x: NDArray, k: int, w: NDArray, verbose=True) -> NDArray:
    """ Determine centroids for a set of k clusters such that when each
    vector in x is assigned to the nearest cluster, the sum of distances
    between each vector and its corresponding centroid is minimized.

    :param x: 2D array of vectors to cluster
    :param k: number of clusters
    :param w: 1D array of weights corresponding to vectors in X
    :param verbose: whether to print info after each training iteration
    :return: 2D array of centroids, number of rows is k
    """
    x = x.copy().astype('float32')  # faiss library needs C-contiguous, float32 arrays
    npoints, ndims = x.shape

    kmeans = faiss.Kmeans(d=ndims, k=k, seed=0, niter=100, nredo=10,
                          verbose=verbose, max_points_per_centroid=npoints)
    kmeans.train(x, weights=w.astype('float32'))

    return kmeans.centroids


def cluster_l2(x: NDArray, centroids: NDArray) -> NDArray:
    """ Cluster the vectors in x according to a given list of cluster
    centroids. Each vector is assigned a cluster ID which is the
    index of the nearest centroid using the Euclidean distance.

    :param x: 2D array of vector to cluster
    :param centroids: 2D array of cluster centroids
    :return: 1D array of cluster IDs
    """
    x = x.copy().astype('float32')
    centroids = centroids.copy().astype('float32')
    npoints, ndims = x.shape

    index = faiss.IndexFlatL2(ndims)
    index.add(centroids)
    _, result = index.search(x, k=1)

    clusterids = [i[0] for i in result]  # index.search() returns array of length-1 arrays
    clusterids = np.array(clusterids).astype('int')

    return clusterids


def umap_reduce(x: NDArray, d: int, n_neighbors: int, min_dist: float) -> NDArray:
    """ Project the vectors in x from their native dimensionality to d dimensions
    using UMAP. UMAP is a nonlinear, topology-preserving dimensionality reduction
    algorithm which transforms a set of points from a higher to a lower dimension
    in such a way that the spatial relationships between points are preserved.

    :param x: 2D array of vectors to be transformed
    :param d: points are projected into this dimensionality (e.g. 3 for 3D)
    :param n_neighbors: UMAP `n_neighbors` parameter
    :param min_dist: UMAP `min_dist` parameter
    :return: 2D array of projected points with d columns
    """
    fit = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        n_components=d,
        metric='euclidean',
        random_state=0
    )
    return fit.fit_transform(x)
