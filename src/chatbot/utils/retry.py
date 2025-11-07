"""Retry helpers for IO-bound operations."""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


@dataclass(frozen=True)
class RetryConfig:
    """Configuration controlling retry behaviour."""

    attempts: int = 3
    base_delay: float = 0.5
    backoff: float = 2.0
    max_delay: float = 10.0
    jitter: float = 0.1


@dataclass
class RetryState:
    """Captures the state of an individual retry loop."""

    attempt: int
    last_exception: Exception | None = None
    delay: float = 0.0


def _next_delay(config: RetryConfig, attempt: int) -> float:
    delay = min(config.base_delay * (config.backoff ** (attempt - 1)), config.max_delay)
    if config.jitter:
        delay += random.uniform(0, config.jitter)
    return delay


def retry(
    *,
    config: RetryConfig | None = None,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    before_sleep: Callable[[RetryState], None] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator implementing exponential backoff for synchronous functions."""

    retry_config = config or RetryConfig()

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            state = RetryState(attempt=1)

            while state.attempt <= retry_config.attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    state.last_exception = exc
                    if state.attempt == retry_config.attempts:
                        raise

                    state.delay = _next_delay(retry_config, state.attempt)
                    if before_sleep is not None:
                        before_sleep(state)
                    time.sleep(state.delay)
                    state.attempt += 1

            # The loop either returns or raises; this is just for type checking.
            raise RuntimeError("retry loop exited unexpectedly")

        return wrapper

    return decorator


def async_retry(
    *,
    config: RetryConfig | None = None,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    before_sleep: Callable[[RetryState], Awaitable[None]] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator implementing exponential backoff for async functions."""

    retry_config = config or RetryConfig()

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            state = RetryState(attempt=1)

            while state.attempt <= retry_config.attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    state.last_exception = exc
                    if state.attempt == retry_config.attempts:
                        raise

                    state.delay = _next_delay(retry_config, state.attempt)
                    if before_sleep is not None:
                        await before_sleep(state)
                    await asyncio.sleep(state.delay)
                    state.attempt += 1

            raise RuntimeError("async retry loop exited unexpectedly")

        return wrapper

    return decorator


def exponential_backoff(
    attempt: int,
    *,
    base: float = 1.0,
    factor: float = 2.0,
    max_delay: float = 60.0,
    jitter_ratio: float = 0.1,
) -> float:
    """Return jittered exponential backoff for the provided attempt number."""

    bounded_attempt = attempt if attempt > 0 else 1
    delay = base * (factor ** (bounded_attempt - 1))
    delay = min(delay, max_delay)
    jitter = random.uniform(0, delay * jitter_ratio) if jitter_ratio else 0.0
    return delay + jitter
