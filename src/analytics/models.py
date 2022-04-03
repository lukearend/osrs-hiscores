""" Contains core machine learning models. """

import json
import os

import faiss
import numpy as np
import umap
from pathlib import Path
from typing import Dict
from numpy.typing import NDArray

os.environ["KMP_WARNINGS"] = 'off'  # suppress OMP deprecation warning from UMAP (github.com/numba/numba/issues/5275)


def load_kmeans_params(file: str = None) -> Dict[str, int]:
    """ Load parameters for running k-means.
    :param file: load from this local file (optional, otherwise uses default location)
    :return: mapping from split names to k values
    """
    params_file = Path(__file__).resolve().parents[2] / "ref" / "kmeans_params.json"
    if file:
        params_file = file
    with open(params_file, 'r') as f:
        return json.load(f)


def load_umap_params(file: str = None) -> Dict[str, Dict]:
    """ Load parameters for running UMAP.
    :param file: load from this local file (optional, otherwise uses default location)
    :return: mapping from split names to UMAP parameter sets
    """
    params_file = Path(__file__).resolve().parents[2] / "ref" / "umap_params.json"
    if file:
        params_file = file
    with open(params_file, 'r') as f:
        return json.load(f)


def fit_kmeans(X: NDArray, k: int, w: NDArray, verbose=True) -> NDArray:
    """
    Determine centroids for a set of k clusters such that when each
    vector in X is assigned to the nearest cluster, the sum of distances
    between each vector and its corresponding centroid is minimized.

    :param X: 2D array of vectors to train on
    :param k: number of clusters
    :param w: 1D array of weights corresponding to vectors in X
    :param verbose: whether to print info after each training iteration
    :return: 2D array of centroids, number of rows is k
    """
    npoints, ndims = X.shape
    kmeans = faiss.Kmeans(ndims, k, seed=0, niter=100, nredo=10,
                          verbose=verbose, max_points_per_centroid=npoints)
    kmeans.train(X.astype('float32'), weights=w.astype('float32'))
    return kmeans.centroids


def cluster_l2(X: NDArray, centroids: NDArray) -> NDArray:
    """
    Cluster the vectors in X according to a given list of cluster
    centroids. Each vector is assigned a cluster ID which is the
    index of the nearest centroid using the Euclidean distance.

    :param X: 2D array of vector to cluster
    :param centroids: 2D array of cluster centroids
    :return: 1D array of cluster IDs
    """
    index = faiss.IndexFlatL2(centroids.shape[1])
    index.add(centroids.astype('float32'))
    _, ids = index.search(X.astype('float32'), k=1)
    ids = [i[0] for i in ids]  # index.search() returns an array of length-1 arrays
    return np.array(ids).astype('int')


def umap_reduce(X: NDArray, d: int, n_neighbors: int, min_dist: float) -> NDArray:
    """
    Project the vectors in X from their native dimensionality to
    d dimensions using UMAP. UMAP is a nonlinear, topology-preserving
    dimensionality reduction algorithm which transforms a set of points
    from a higher to a lower dimension in such a way that the spatial
    relationships between points are preserved.

    :param X: 2D array of vectors to be transformed
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
    return fit.fit_transform(X)
