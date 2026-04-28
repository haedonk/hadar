import asyncio
import logging

logger = logging.getLogger(__name__)


class EnergyEventQueue:
    def __init__(self, max_size: int = 10):
        logger.debug(f"Initializing EnergyEventQueue with max_size={max_size}")
        self.queue = asyncio.Queue(maxsize=max_size)

    async def add_event(self, event):
        logger.debug(f"Adding event to queue: {event}")
        await self.queue.put(event)

    async def get_event(self):
        logger.debug("Getting event from queue.")
        return await self.queue.get()

    async def clear(self):
        logger.debug("Clearing event queue.")
        while not self.queue.empty():
            self.queue.get_nowait()
            self.queue.task_done()

    def is_empty(self):
        empty = self.queue.empty()
        logger.debug(f"Queue is_empty: {empty}")
        return empty

    def is_full(self):
        full = self.queue.full()
        logger.debug(f"Queue is_full: {full}")
        return full


class TemperatureEventQueue:
    def __init__(self, max_size: int = 10):
        logger.debug(f"Initializing TemperatureEventQueue with max_size={max_size}")
        self.queue = asyncio.Queue(maxsize=max_size)

    async def add_event(self, event):
        logger.debug(f"Adding event to queue: {event}")
        await self.queue.put(event)

    async def get_event(self):
        logger.debug("Getting event from queue.")
        return await self.queue.get()

    async def clear(self):
        logger.debug("Clearing event queue.")
        while not self.queue.empty():
            self.queue.get_nowait()
            self.queue.task_done()

    def is_empty(self):
        empty = self.queue.empty()
        logger.debug(f"Queue is_empty: {empty}")
        return empty

    def is_full(self):
        full = self.queue.full()
        logger.debug(f"Queue is_full: {full}")
        return full
