import asyncio
import random
from pathlib import Path
from typing import Dict, Any

import aiohttp
import pytest

from src.common import env_var, connect_mongo, osrs_skills, osrs_csv_api_stats
from src.scrape import (PlayerRecord, get_hiscores_page, get_player_stats,
                        player_to_mongodoc, mongodoc_to_player)
from src.scrape.scrape_hiscores import build_pagejobs_list

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
        front_page = await get_hiscores_page(sess, page_num=1)
        top_player_name = front_page[0]  # setup: get "Lynx Titan", or whatever he may change his name to

        top_player: PlayerRecord = await get_player_stats(sess, username=top_player_name)
        assert top_player.rank == 1
        assert top_player.total_level == 2277
        assert top_player.total_xp == 4_600_000_000

        # Lynx Titan is 200m all, so his individual stat rankings are fixed forever.
        expected_ranks = {
            'attack': 15, 'defence': 28, 'strength': 18, 'hitpoints': 7, 'ranged': 8, 'prayer': 11,
            'magic': 32, 'cooking': 160, 'woodcutting': 15, 'fletching': 12, 'fishing': 9,
            'firemaking': 48, 'crafting': 4, 'smithing': 3, 'mining': 25, 'herblore': 5, 'agility': 23,
            'thieving': 12, 'slayer': 2, 'farming': 19, 'runecraft': 7, 'hunter': 4, 'construction': 4
        }
        for skill in osrs_skills():
            rank_i = osrs_csv_api_stats().index(f"{skill}_rank")
            lvl_i = osrs_csv_api_stats().index(f"{skill}_level")
            xp_i = osrs_csv_api_stats().index(f"{skill}_xp")
            assert top_player.stats[rank_i] == expected_ranks[skill]
            assert top_player.stats[lvl_i] == 99
            assert top_player.stats[xp_i] == 200_000_000


def test_read_write_scrape_records():
    db = connect_mongo(mongo_url)
    coll = db['scrape-test']
    coll.drop()
    async def get_player():
        async with aiohttp.ClientSession() as sess:
            return await get_player_stats(sess, username="snakeylime")
    before_player = asyncio.run(get_player())

    before_doc: Dict[str, Any] = player_to_mongodoc(before_player)
    coll.insert_one(before_doc)
    after_doc = coll.find_one({"username": "snakeylime"})
    del before_doc['_id']  # strangely, '_id' is added to before_doc after insertion
    del after_doc['_id']
    assert before_doc == after_doc

    after_player: PlayerRecord = mongodoc_to_player(after_doc)
    assert before_player == after_player


def test_build_page_jobs():
    with pytest.raises(ValueError):
        pages = build_pagejobs_list(start_rank=26, end_rank=25)

    pages = build_pagejobs_list(start_rank=1, end_rank=25)
    assert len(pages) == 1
    assert pages[0].startind == 0
    assert pages[0].endind == 25

    pages = build_pagejobs_list(start_rank=5, end_rank=55)
    assert len(pages) == 3
    assert pages[0].startind == 4
    assert pages[0].endind == 25
    assert pages[1].startind == 0
    assert pages[1].endind == 25
    assert pages[2].startind == 0
    assert pages[2].endind == 5

    pages = build_pagejobs_list(start_rank=1, end_rank=2_000_000)
    assert len(pages) == 80_000
    assert pages[0].startind == 0
    assert pages[-1].endind == 25



if __name__ == '__main__':
    test_build_page_jobs()


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
