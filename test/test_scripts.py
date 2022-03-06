from src.common import line_count, skill_splits
from src.models import fit_clusters, cluster_players, dim_reduce_clusters, kmeans_params
from src.results import (postprocess_clusters, build_app_data,
                         load_clusters_xyz, load_cluster_analytics, load_app_data)
from test import FilePaths
fp = FilePaths()


def test_build_test_data():
    assert line_count(fp.stats) - 1 == 10000


def test_fit_clusters():
    fit_clusters.main(fp.stats, fp.centroids, fp.kmeans_params, verbose=False)
    params = kmeans_params(fp.kmeans_params)
    nclusters_across_splits = sum(params.values())
    assert line_count(fp.centroids) - 1 == nclusters_across_splits


def test_cluster_players():
    cluster_players.main(fp.stats, fp.centroids, fp.clusters)
    assert line_count(fp.clusters) - 1 == line_count(fp.stats) - 1


def test_dim_reduce_clusters():
    dim_reduce_clusters.main(fp.centroids, fp.clusters_xyz, fp.umap_params)
    xyz_per_split = load_clusters_xyz(fp.clusters_xyz)
    for splitname, nclusters in kmeans_params(fp.kmeans_params).items():
        xyz_data = xyz_per_split[splitname]
        # assert xyz_data.shape == (nclusters, 3)  # TODO: uncomment when umap params frozen


def test_postprocess_clusters():
    postprocess_clusters.main(fp.stats, fp.clusters, fp.cluster_analytics)
    analytics_per_split = load_cluster_analytics(fp.cluster_analytics)
    k_per_split = kmeans_params(fp.kmeans_params)
    for split in skill_splits():
        nclusters = k_per_split[split.name]
        analytics = analytics_per_split[split.name]
        assert len(analytics.sizes) == nclusters
        assert len(analytics.uniqueness) == nclusters
        assert analytics.quartiles.shape == (nclusters, 5, split.nskills)


def test_build_app_data():
    build_app_data.main(fp.centroids, fp.cluster_analytics, fp.clusters_xyz, fp.app_data)
    app_data = load_app_data(fp.app_data)
    k_per_split = kmeans_params(fp.kmeans_params)
    splits = skill_splits()
    assert app_data.splitnames == [s.name for s in splits]
    for split in skill_splits():
        splitdata = app_data.splitdata[split.name]
        assert splitdata.skills == split.skills
        # assert splitdata.axlims.shape == (3, 2)  # TODO: uncomment when umap params frozen

        nclusters = k_per_split[split.name]
        cdata = splitdata.clusterdata
        assert len(cdata.sizes) == nclusters
        assert len(cdata.uniqueness) == nclusters
        assert cdata.quartiles.shape == (nclusters, 5, split.nskills)
        assert cdata.centroids.shape == (nclusters, split.nskills)
        # assert cdata.xyz.shape == (nclusters, 3)  # TODO: uncomment when umap params frozen
