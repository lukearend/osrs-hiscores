import asyncio
import os
import random
from pathlib import Path
from typing import Tuple, List

import aiohttp
import pytest

from src import connect_mongo, osrs_skills, csv_api_stats
from src.scrape import PlayerRecord, JobCounter, get_page_range
from src.scrape.export import player_to_csv, csv_to_player, get_top_rank
from src.scrape.requests import get_hiscores_page, get_player_stats
from src.scrape.workers import JobQueue
from scripts.scrape_hiscores import main

test_dir = Path(__file__).resolve().parent
mongo_url = "localhost:27017"


@pytest.mark.asyncio
async def test_get_page_usernames():
    async with aiohttp.ClientSession() as sess:
        for _ in range(3):
            random_page = random.randint(1, 80000)
            usernames = await get_hiscores_page(sess, random_page)
            assert len(set(usernames)) == 25


@pytest.mark.asyncio
async def test_get_player_stats():
    async with aiohttp.ClientSession() as sess:
        front_page: List[Tuple[int, str]] = await get_hiscores_page(sess, page_num=1)
        top_player_name = front_page[0][1]

        top_player: PlayerRecord = await get_player_stats(sess, username=top_player_name)
        assert top_player.rank == 1
        assert top_player.total_level == 2277
        assert top_player.total_xp == 4_600_000_000

        for skill in osrs_skills():
            lvl_ind = csv_api_stats().index(f"{skill}_level")
            xp_ind = csv_api_stats().index(f"{skill}_xp")
            assert top_player.stats[lvl_ind] == 99
            assert top_player.stats[xp_ind] == 200_000_000


def test_build_page_jobs():
    with pytest.raises(ValueError):
        get_page_range(start_rank=26, end_rank=25)
    with pytest.raises(ValueError):
        get_page_range(start_rank=0, end_rank=25)
    with pytest.raises(ValueError):
        get_page_range(start_rank=1, end_rank=2_000_050)

    firstpage, startind, lastpage, endind = get_page_range(start_rank=1, end_rank=25)
    assert firstpage == lastpage == 1
    assert startind == 0
    assert endind == 25

    firstpage, startind, lastpage, endind = get_page_range(start_rank=26, end_rank=2_000_000)
    assert firstpage == 2
    assert startind == 0
    assert lastpage == 80000
    assert endind == 25

    firstpage, startind, lastpage, endind = get_page_range(start_rank=5, end_rank=55)
    assert firstpage == 1
    assert startind == 4
    assert lastpage == 3
    assert endind == 5


def test_convert_player_csv():
    db = connect_mongo(mongo_url)
    coll = db['scrape-test']
    coll.drop()

    async def get_player():
        async with aiohttp.ClientSession() as sess:
            return await get_player_stats(sess, username="snakeylime")
    player = asyncio.run(get_player())

    player_csv: str = player_to_csv(player)
    player_restored: PlayerRecord = csv_to_player(player_csv)
    assert player == player_restored


@pytest.mark.asyncio
async def test_jobqueue():
    q = JobQueue(maxsize=3)
    await q.put(1)
    await q.put(4)
    await q.put(3)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(q.put(2), timeout=0.1)
    await q.put(2, force=True)
    assert await q.get() == 1
    assert await q.get() == 2
    assert await q.get() == 3
    assert await q.get() == 4


@pytest.mark.asyncio
async def test_jobcounter():
    jc = JobCounter(value=5)
    assert jc.value == 5

    async def call_next():
        await asyncio.sleep(0.25)
        jc.next()
    asyncio.create_task(call_next())

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(jc.await_next(), timeout=0.1)
    await asyncio.wait_for(jc.await_next(), timeout=0.25)
    assert jc.value == 6


@pytest.mark.asyncio
async def test_scrape_main():
    outfile = 'data/scrape.out'
    start_rank = random.randint(1_500_000, 2_000_000) - 100
    end_rank = start_rank + 50
    if os.path.isfile(outfile):
        os.remove(outfile)
    await main(outfile, start_rank=start_rank, stop_rank=end_rank, nworkers=25)
    assert get_top_rank(outfile) == end_rank


# from pymongo import MongoClient
#
# from src.common import line_count, mongodoc_to_playerdata, osrs_statnames, load_splits
# from src.models import fit_clusters, cluster_players, dim_reduce_clusters, load_kmeans_params
# from src.results import (postprocess_clusters, build_app_data, build_database,
#                          load_clusters_xyz, load_cluster_analytics, load_app_data)
# from test import FilePaths
#
# fp = FilePaths()
# pagerange = (1, 20)
# nplayers = None


# def test_fit_clusters():
#     fit_clusters.main(fp.stats, fp.centroids, fp.kmeans_params, verbose=False)
#     k_per_split = load_kmeans_params(fp.kmeans_params)
#     nclusters_across_splits = sum(k_per_split.values())
#     assert line_count(fp.centroids) - 1 == nclusters_across_splits
#
#
# def test_cluster_players():
#     cluster_players.main(fp.stats, fp.centroids, fp.clusters)
#     assert line_count(fp.clusters) - 1 == line_count(fp.stats) - 1
#
#
# def test_dim_reduce_clusters():
#     dim_reduce_clusters.main(fp.centroids, fp.clusters_xyz, fp.umap_params)
#     xyz_per_split = load_clusters_xyz(fp.clusters_xyz)
#     for splitname, nclusters in load_kmeans_params(fp.kmeans_params).items():
#         xyz_data = xyz_per_split[splitname]
#         # assert xyz_data.shape == (nclusters, 3)  # TODO: uncomment when umap params frozen
#
#
# def test_postprocess_clusters():
#     postprocess_clusters.main(fp.stats, fp.clusters, fp.cluster_analytics)
#     analytics_per_split = load_cluster_analytics(fp.cluster_analytics)
#     k_per_split = load_kmeans_params(fp.kmeans_params)
#     for split in load_skill_splits():
#         nclusters = k_per_split[split.name]
#         analytics = analytics_per_split[split.name]
#         assert len(analytics.sizes) == nclusters
#         assert len(analytics.uniqueness) == nclusters
#         assert analytics.quartiles.shape == (nclusters, 5, 1 + split.nskills)  # includes total as first skill col
#
#
# def test_build_app_data():
#     build_app_data.main(fp.centroids, fp.cluster_analytics, fp.clusters_xyz, fp.app_data)
#     app_data = load_app_data(fp.app_data)
#     k_per_split = load_kmeans_params(fp.kmeans_params)
#     splits = load_skill_splits()
#     assert app_data.splitnames == [s.name for s in splits]
#     for split in splits:
#         splitdata = app_data.splitdata[split.name]
#         assert splitdata.skills == split.skills
#         # assert splitdata.axlims.shape == (3, 2)  # TODO: uncomment when umap params frozen
#
#         nclusters = k_per_split[split.name]
#         cdata = splitdata.clusterdata
#         assert len(cdata.sizes) == nclusters
#         assert len(cdata.uniqueness) == nclusters
#         assert cdata.quartiles.shape == (nclusters, 5, 1 + split.nskills)
#         assert cdata.centroids.shape == (nclusters, split.nskills)
#         # assert cdata.xyz.shape == (nclusters, 3)  # TODO: uncomment when umap params frozen
#
#
# def test_build_database():
#     test_url = "localhost:27017"
#     test_coll = 'players-test'
#     # build_database.main(fp.stats, fp.clusters, url=test_url, coll_name=test_coll, drop=True)
#
#     client = MongoClient(test_url)
#     player_record = client['osrs-hiscores']['players-test'].find_one({})
#     player = mongodoc_to_playerdata(player_record)
#     assert len(player.stats) == len(osrs_statnames())
#     # todo: continue
