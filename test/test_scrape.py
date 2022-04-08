import asyncio
import os
import random
from typing import Tuple, List

import aiohttp
import pytest

from src.common import osrs_skills
from src.scrape import PlayerRecord, JobCounter, player_to_csv, csv_to_player, csv_api_stats
from src.scrape.export import get_top_rank, get_page_jobs
from src.scrape.requests import get_hiscores_page, get_player_stats
from src.scrape.workers import JobQueue
from scripts.scrape_hiscores import main


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
        get_page_jobs(start_rank=26, end_rank=25)
    with pytest.raises(ValueError):
        get_page_jobs(start_rank=0, end_rank=25)
    with pytest.raises(ValueError):
        get_page_jobs(start_rank=1, end_rank=2_000_050)

    jobs = get_page_jobs(start_rank=1, end_rank=25)
    assert len(jobs) == 1
    assert jobs[0].pagenum == jobs[-1].pagenum == 1
    assert jobs[0].startind == 0
    assert jobs[-1].endind == 25

    jobs = get_page_jobs(start_rank=26, end_rank=2_000_000)
    assert len(jobs) == 79999
    assert jobs[0].pagenum == 2
    assert jobs[0].startind == 0
    assert jobs[-1].pagenum == 80000
    assert jobs[-1].endind == 25

    jobs = get_page_jobs(start_rank=5, end_rank=55)
    assert len(jobs) == 3
    assert jobs[0].pagenum == 1
    assert jobs[0].startind == 4
    assert jobs[-1].pagenum == 3
    assert jobs[-1].endind == 5


def test_convert_player_csv():
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
    out_file = 'test-scrape.csv'
    start_rank = random.randint(1, 2_000_000) - 100
    end_rank = start_rank + 49
    if os.path.isfile(out_file):
        os.remove(out_file)
    await main(out_file, start_rank=start_rank, stop_rank=end_rank, nworkers=25)
    assert get_top_rank(out_file) == end_rank
