from types import GeneratorType, CoroutineType
import asyncio
import random

FORKS: list[asyncio.Lock]


async def philosopher(id: int, footman: asyncio.Semaphore) -> tuple[int, float, float]:
    async with footman:  # async context manager
        async with FORKS[id], FORKS[(id + 1) % len(FORKS)]:  # async context manager
            eat_time = 1 + random.random()
            print(f"{id} eating")
            await asyncio.sleep(eat_time)
            think_time = 1 + random.random()
            print(f"{id} philosophizing")
            await asyncio.sleep(think_time)
    return id, eat_time, think_time


async def main(faculty: int = 5, servings: int = 5) -> None:
    global FORKS
    FORKS = [asyncio.Lock() for i in range(faculty)]
    footman = asyncio.BoundedSemaphore(faculty - 1)
    for serving in range(servings):
        department: GeneratorType[CoroutineType] = (
            philosopher(p, footman) for p in range(faculty)
        )

        # gets the values from the coroutine
        results: list = await asyncio.gather(*department)
        print(results)


def runner():
    asyncio.run(main(5, 1))
