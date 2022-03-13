import argparse
import asyncio
from dataclasses import dataclass


@dataclass
class PageJob:
    pagenum: int
    startind: int = 0  # start index of the usernames wanted from this page
    endind: int = 25   # end index of the usernames wanted from this page


@dataclass
class UserJob:
    priority: int
    username: str


def init_page_jobs(start_rank, end_rank) -> asyncio.PriorityQueue:
    job_queue = asyncio.PriorityQueue()
    page = PageJob(pagenum=None)
    page.pagenum = (start_rank - 1) // 25 + 1
    page.startind = (start_rank - 1) % 25
    for rank in range(start_rank, end_rank + 1):
        if rank == end_rank:
            page.endind = (rank - 1 % 25) + 1
            job_queue.put((rank, page))
            break
        elif rank % 25 == 0:
            page.endind = 25
            job_queue.put((rank, page))
            page.startind = 0
            page.pagenum += 1

    # todo: can you precompute pages and iterate that way?
    # todo: ... and is that cleaner?

    return job_queue



async def main(mongo_url: str, mongo_coll: str, start_rank: int, stop_rank: int):
    done = False

    page_jobs = asyncio.PriorityQueue()
    for priority, page_num in enumerate(range(start_rank, stop_rank + 1)):
        page_job_queue.put_nowait((priority, page_num))

    username_job_queue = asyncio.PriorityQueue()
    for priority,

    while not done:
        while True:
            pages_to_proces




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""Download player data from OSRS hiscores into MongoDB.""")
    parser.add_argument('--mongo-url', required=True, help="store data in Mongo instance running at this URL")
    parser.add_argument('--mongo-coll', required=True, help="put scraped data into this collection")
    parser.add_argument('--start', required=True, help="start data collection at this player rank")
    parser.add_argument('--stop', required=True, help="stop data collection at this rank")
    parser.parse_args()
    asyncio.run(main(args.mongo_url, args.mongo_coll, args.start, args.stop))
