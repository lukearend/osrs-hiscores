""" Scrape data from the OSRS hiscores until hitting an exception. """

import asyncio

import aiohttp

from src.scrape.export import get_page_jobs, export_records
from src.scrape.common import DoneScraping
from src.scrape.workers import JobQueue, JobCounter, Worker, \
    request_page, request_stats, enqueue_page_usernames, enqueue_stats


N_PAGE_WORKERS = 2   # number of page workers downloading rank/username info
UNAME_BUFSIZE = 100  # maximum length of buffer containing username jobs for stats workers


async def scrape_hiscores(start_rank, stop_rank, out_file, num_workers):

    # Build the job queues connecting each stage of the processing pipeline.
    joblist = get_page_jobs(start_rank, stop_rank)
    page_q = JobQueue()
    for job in joblist:
        await page_q.put(job)
    uname_q = JobQueue(maxsize=UNAME_BUFSIZE)
    export_q = asyncio.Queue()

    # Scraping happens in two stages. First the page workers download front pages
    # of the hiscores and extract usernames in ranked order. Then the stats workers
    # receive usernames and query the CSV API for the corresponding account stats.
    currentpage = JobCounter(value=joblist[0].pagenum)
    pageworkers = [Worker(in_queue=page_q, out_queue=uname_q, job_counter=currentpage)
                   for _ in range(N_PAGE_WORKERS)]

    currentrank = JobCounter(value=start_rank)
    statworkers = [Worker(in_queue=uname_q, out_queue=export_q, job_counter=currentrank)
                   for _ in range(num_workers)]

    # Spawn the data scraping tasks and run until requests fail.
    async with aiohttp.ClientSession() as sess:
        T = [asyncio.create_task(
            export_records(in_queue=export_q, out_file=out_file, total=stop_rank - currentrank.value + 1)
        )]
        for w in pageworkers:
            T.append(asyncio.create_task(
                w.run(sess, request_fn=request_page, enqueue_fn=enqueue_page_usernames)
            ))
        for i, w in enumerate(statworkers):
            T.append(asyncio.create_task(
                w.run(sess, request_fn=request_stats, enqueue_fn=enqueue_stats, delay=i * 0.1)
            ))
        try:
            await asyncio.gather(*T)  # allow first exception to be caught
        except DoneScraping:
            pass
        finally:
            for task in T:
                task.cancel()
            await asyncio.gather(*T, return_exceptions=True)  # suppress CancelledErrors
