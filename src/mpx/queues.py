import os
import time

from collections.abc import Iterator
from pathlib import Path
from multiprocessing import Queue, Process, cpu_count
from fnmatch import fnmatch

type Query_Q = Queue[str | None]
type Result_Q = Queue[list[str]]


def search(paths: list[Path], query_q: Query_Q, results_q: Result_Q) -> None:
    print(f"PID: {os.getpid()}, paths {len(paths)}")
    lines: list[str] = []

    for path in paths:
        lines.extend(line.rstrip() for line in path.read_text().splitlines())

    while True:
        if (query_text := query_q.get()) is None:
            break

        results = [line for line in lines if query_text in line]
        results_q.put(results)


class DirectorySearch:
    def __init__(self) -> None:
        self.query_queues: list[Query_Q]
        self.results_queue: Result_Q
        self.search_workers: list[Process]

    def setup_search(self, paths: list[Path], cpus: int | None = None) -> None:
        if cpus is None:
            cpus = cpu_count()

        worker_paths = [paths[i::cpus] for i in range(cpus)]
        self.query_queues = [Queue() for p in range(cpus)]
        self.results_queue = Queue()

        self.search_workers = [
            Process(target=search, args=(paths, query_queue, self.results_queue))
            for paths, query_queue in zip(worker_paths, self.query_queues)
        ]
        for proc in self.search_workers:
            proc.start()

    def teardow_search(self) -> None:
        # signals process termination
        for query_queue in self.query_queues:
            query_queue.put(None)

        for proc in self.search_workers:
            proc.join()

    def search(self, target: str) -> Iterator[str]:
        for q in self.query_queues:
            q.put(target)

        for i in range(len(self.query_queues)):
            for match in self.results_queue.get():
                yield match


def all_source(path: Path, pattern: str) -> Iterator[Path]:
    for root, dirs, files in os.walk(path):
        for skip in {".tox", ".mypy_cache", "__pycache__", ".idea", ".vscode", ".venv"}:
            if skip in dirs:
                dirs.remove(skip)

        yield from (Path(root) / f for f in files if fnmatch(f, pattern))


def main():
    ds = DirectorySearch()
    base = Path.cwd().parent
    all_paths = list(all_source(base, "*.py"))

    ds.setup_search(all_paths)

    for target in ("import", "class", "def"):
        start = time.perf_counter()
        count = 0

        for line in ds.search(target):
            count += 1

        milliseconds = 1000 * (time.perf_counter() - start)
        print(
            f"Found {count} {target!r} in {len(all_paths)} files in {milliseconds:.3f}ms"
        )

    ds.teardow_search()
