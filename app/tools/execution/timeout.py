# app/tools/execution/timeout.py

import asyncio
import inspect
from functools import partial
from typing import Any, Callable


class ToolTimeoutError(Exception):
    """Tool execution exceeded its allowed time."""


async def execute_with_timeout(
    handler: Callable[..., Any],
    arguments: dict[str, Any],
    timeout_seconds: float,
) -> Any:

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")

    if inspect.iscoroutinefunction(handler):
        operation = handler(**arguments)
    else:
        operation = asyncio.to_thread(
            partial(handler, **arguments)
        )

    try:
        return await asyncio.wait_for(
            operation,
            timeout=timeout_seconds,
        )

    except TimeoutError as exc:
        raise ToolTimeoutError(
            f"Tool exceeded {timeout_seconds} seconds"
        ) from exc
