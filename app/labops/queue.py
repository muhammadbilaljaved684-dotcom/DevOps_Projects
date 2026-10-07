"""Job queue. Redis list in clusters, in-memory deque for tests.

Jobs carry the measurement id and the enqueue timestamp so the worker can
measure end-to-end latency (upload -> result), which is the SLI behind the
main SLO: 99% of uploads processed within 30 seconds.
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Job:
    measurement_id: str
    enqueued_at: float

    def dumps(self) -> str:
        return json.dumps({"id": self.measurement_id, "t": self.enqueued_at})

    @classmethod
    def loads(cls, raw: str | bytes) -> Job:
        d = json.loads(raw)
        return cls(measurement_id=d["id"], enqueued_at=float(d["t"]))


class Queue(Protocol):
    def put(self, measurement_id: str) -> Job: ...
    def get(self, timeout: int) -> Job | None: ...
    def depth(self) -> int: ...
    def ping(self) -> bool: ...


class MemoryQueue:
    def __init__(self) -> None:
        self._q: deque[str] = deque()

    def put(self, measurement_id: str) -> Job:
        job = Job(measurement_id, time.time())
        self._q.append(job.dumps())
        return job

    def get(self, timeout: int = 0) -> Job | None:
        return Job.loads(self._q.popleft()) if self._q else None

    def depth(self) -> int:
        return len(self._q)

    def ping(self) -> bool:
        return True


class RedisQueue:
    def __init__(self, url: str, name: str) -> None:
        import redis  # imported lazily so tests don't need a server

        self._r = redis.Redis.from_url(url, socket_timeout=10, health_check_interval=30)
        self._name = name

    def put(self, measurement_id: str) -> Job:
        job = Job(measurement_id, time.time())
        self._r.lpush(self._name, job.dumps())
        return job

    def get(self, timeout: int = 5) -> Job | None:
        item = self._r.brpop([self._name], timeout=timeout)
        return Job.loads(item[1]) if item else None

    def depth(self) -> int:
        return int(self._r.llen(self._name))

    def ping(self) -> bool:
        return bool(self._r.ping())


def make_queue(backend: str, redis_url: str, name: str) -> Queue:
    if backend == "redis":
        return RedisQueue(redis_url, name)
    if backend == "memory":
        return MemoryQueue()
    raise ValueError(f"unknown queue backend: {backend}")
