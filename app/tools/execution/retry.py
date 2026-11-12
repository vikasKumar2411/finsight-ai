
# app/tools/execution/retry.py

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class TransientToolError(Exception):
    """A temporary failure that may be safe to retry."""


class ToolRetryExhaustedError(Exception):
    """All permitted tool attempts have failed."""


async def execute_with_retry(
    operation: Callable[[], Awaitable[T]],
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    backoff_multiplier: float = 2.0,
    maximum_delay: float = 5.0,
    retryable_exceptions: tuple[type[Exception], ...] = (
        TransientToolError,
    ),
) -> T:

    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    delay = initial_delay

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()

        except retryable_exceptions as exc:
            if attempt == max_attempts:
                raise ToolRetryExhaustedError(
                    f"Tool failed after {max_attempts} attempts"
                ) from exc

            await asyncio.sleep(delay)

            delay = min(
                delay * backoff_multiplier,
                maximum_delay,
            )

    raise RuntimeError("Unreachable retry state")
