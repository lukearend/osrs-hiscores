import asyncio
import aiohttp
import numpy as np

from src.scrape import request_hiscores_page, parse_page_html, request_stats


async def scrape_page(sess, num):
    page_html = await request_hiscores_page(sess, page_num=num)
    page_data = parse_page_html(page_html)

    usernames = []
    stats = np.zeros(
    for rank, playerinfo in page_data.items():
        uname = playerinfo['username']

        stats_csv = await request_stats(sess, uname)
        print(stats_csv)


async def query_player_stats(sess, username):
    csv_values = await request_stats(sess, username)
    values = csv_values.split(',')
    username = values.pop(0)
    stats = values[:72]  # 23 skills + total, each with rank/level/xp
    stats = np.array(stats, dtype='int')
    stats[stats < 0] == -1
    return username, stats


async def main(num):
    # pages_to_scrape = range(start_page, end_page + 1)
    # job_queue = asyncio.Queue()
    # for page_num in pages_to_scrape:
    #     job_queue.put_nowait(page_num)

    async with aiohttp.ClientSession() as sess:
        # await scrape_page(sess, num)
        uname, stats = await query_player_stats(sess, 'snakeylime')
        print(uname)
        print(stats)


asyncio.run(main(5))
