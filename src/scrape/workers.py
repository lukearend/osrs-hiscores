import asyncio
from asyncio import Queue, Event, CancelledError
from dataclasses import dataclass
from typing import List, Tuple, Awaitable, Any

from aiohttp import ClientSession

from src.scrape import printlog
from src.scrape.requests import RequestFailed, UserNotFound, PlayerRecord, get_hiscores_page, get_player_stats


@dataclass
class JobCounter:
    """ A counter shared among workers for keeping track of the current job. """
    value: int = 0


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


class JobQueue:
    """ A priority queue that allows maxsize to be optionally overridden. """
    def __init__(self, maxsize=None):
        self.q = asyncio.PriorityQueue()
        self.removed = asyncio.Event()
        self.maxsize = maxsize

    async def put(self, item, force=False):
        if self.maxsize and not force:
            while self.q.qsize() >= self.maxsize:
                await self.removed.wait()
                self.removed.clear()
        await self.q.put(item)

    async def get(self):
        item = await self.q.get()
        self.removed.set()
        return item

    async def join(self):
        await self.q.join()

    def task_done(self, n=1):
        for _ in range(n):
            self.q.task_done()


class Worker:
    """ An abstract worker which gets a job from an input queue, makes a request
    to the OSRS hiscores, and puts the result on an output queue in such a way
    that job order is preserved by all workers.
    """
    def __init__(self, in_queue: JobQueue, out_queue: Queue, job_counter: JobCounter, next_signal: Event):
        self.in_q = in_queue
        self.out_q = out_queue
        self.nextjob = next_signal
        self.jobcounter = job_counter

    async def run(self, sess: ClientSession, request_fn=Awaitable[Any], enqueue_fn=Awaitable[Any]):
        while True:
            job = await self.in_q.get()
            try:
                if job.result is None:
                    await request_fn(sess, job)

                while self.jobcounter.value < job.priority:
                    await self.nextjob.wait()
                    self.nextjob.clear()

                await enqueue_fn(self.out_q, job)
                self.in_q.task_done()
                self.jobcounter.value += 1
                self.nextjob.set()

            except (CancelledError, RequestFailed):
                await self.in_q.put(job, force=True)
                self.in_q.task_done()
                raise


class PageWorker:
    """ Downloads front pages from the hiscores and enqueues usernames in rank order. """
    currentpage = JobCounter()
    nextpage = asyncio.Event()

    def __init__(self, in_queue: JobQueue, out_queue: JobQueue, init_page: int = 0, name: str = None):
        self.name = name if name else type(self).__name__
        self.worker = Worker(in_queue, out_queue, job_counter=self.currentpage, next_signal=self.nextpage)
        self.currentpage.value = init_page

    async def request_page(self, sess: ClientSession, job: PageJob):
        if job.result is None:
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
    currentrank = JobCounter()
    nextuser = asyncio.Event()

    def __init__(self, in_queue: JobQueue, out_queue: Queue, init_rank: int = 0, name: str = None):
        self.name = name if name else type(self).__name__
        self.worker = Worker(in_queue, out_queue, job_counter=self.currentrank, next_signal=self.nextuser)
        self.currentrank.value = init_rank

    async def request_stats(self, sess: ClientSession, job: UsernameJob):
        try:
            job.result = await get_player_stats(sess, username=job.username)
        except UserNotFound:
            printlog(f"{self.name}: player '{job.username}' not found (rank {job.priority})", 'info')
            job.result = 'notfound'

    async def enqueue_result(self, queue: Queue, job: UsernameJob):
        if job.result != 'notfound':
            player: PlayerRecord = job.result
            await queue.put(player)

    async def run(self, sess: ClientSession, delay: float = 0):
        await asyncio.sleep(delay)
        await self.worker.run(sess, request_fn=self.request_stats, enqueue_fn=self.enqueue_result)
