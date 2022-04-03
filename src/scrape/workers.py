import asyncio
import logging
from asyncio import Queue, CancelledError
from dataclasses import dataclass
from typing import List, Tuple, Awaitable, Any

from aiohttp import ClientSession

from src.scrape import RequestFailed, UserNotFound, ServerBusy, PlayerRecord, JobCounter
from src.scrape.requests import get_hiscores_page, get_player_stats


class JobQueue:
    """ A priority queue that allows maxsize to be optionally overridden. """

    def __init__(self, maxsize=None):
        self.q = asyncio.PriorityQueue()
        self.got = asyncio.Event()
        self.maxsize = maxsize

    async def put(self, item, force=False):
        if self.maxsize and not force:
            while self.q.qsize() >= self.maxsize:
                await self.got.wait()
                self.got.clear()
        await self.q.put(item)

    async def get(self):
        item = await self.q.get()
        self.got.set()
        return item


class Worker:
    """ An abstract worker which gets a job from an input queue, makes a request
    to the OSRS hiscores, and puts the result on an output queue in such a way
    that job order is preserved by all workers.
    """
    def __init__(self, in_queue: JobQueue, out_queue: Queue, job_counter: JobCounter):
        self.in_q = in_queue
        self.out_q = out_queue
        self.jc = job_counter

    async def run(self, sess: ClientSession, request_fn=Awaitable[Any], enqueue_fn=Awaitable[Any]):
        while True:
            job = await self.in_q.get()
            try:
                if job.result is None:
                    await request_fn(sess, job)

                while self.jc.value < job.priority:
                    await self.jc.await_next()

                await enqueue_fn(self.out_q, job)
                self.jc.next()

            except (CancelledError, RequestFailed):
                await self.in_q.put(job, force=True)
                raise


@dataclass(order=True)
class PageJob:
    """ Represents the task of fetching a front page from the OSRS hiscores, parsing
    out the rank/username data, and enqueueing the 25 usernames in rank order. """
    priority: int
    pagenum: int
    startind: int = 0  # index of first rank/username pair we want from this page
    endind: int = 25   # index of last rank/username pair we want from this page
    result: List[Tuple[int, str]] = None  # list of 25 rank/username pairs


@dataclass(order=True)
class UsernameJob:
    """ Represents the task of fetching and enqueueing stats for one account. """
    priority: int
    username: str
    result: PlayerRecord = None


class PageWorker:
    """ Downloads front pages from the hiscores and enqueues usernames in rank order. """

    def __init__(self, in_queue: JobQueue, out_queue: JobQueue, page_counter: JobCounter):
        self.worker = Worker(in_queue, out_queue, job_counter=page_counter)

    async def request_page(self, sess: ClientSession, job: PageJob):
        job.result = await get_hiscores_page(sess, page_num=job.pagenum)

    async def enqueue_usernames(self, queue: Queue, job: PageJob):
        for rank, uname in job.result[job.startind:job.endind]:
            outjob = UsernameJob(priority=rank, username=uname)
            await queue.put(outjob)
            job.startind += 1

    async def run(self, sess: ClientSession):
        await self.worker.run(sess, request_fn=self.request_page, enqueue_fn=self.enqueue_usernames)


class StatsWorker:
    """ Downloads player stats given player usernames. """

    def __init__(self, in_queue: JobQueue, out_queue: Queue, rank_counter: JobCounter):
        self.worker = Worker(in_queue, out_queue, job_counter=rank_counter)

    async def request_stats(self, sess: ClientSession, job: UsernameJob):
        ntries = 0
        while True:
            try:
                job.result = await get_player_stats(sess, username=job.username)
                return
            except UserNotFound as e:
                logging.warning(f"player {e} not found (rank {job.priority})")
                job.result = 'notfound'
                return
            except ServerBusy as e:
                logging.info(f"player '{job.username}' (rank {job.priority}): server busy, {e}")
                await asyncio.sleep(30)  # back off for a bit
                ntries += 1
                if ntries == 3:
                    raise RequestFailed(f"player '{job.username}' (rank {job.priority}): too many retries")

    async def enqueue_result(self, queue: Queue, job: UsernameJob):
        await queue.put(job.result)

    async def run(self, sess: ClientSession, delay: float = 0):
        await asyncio.sleep(delay)
        await self.worker.run(sess, request_fn=self.request_stats, enqueue_fn=self.enqueue_result)
