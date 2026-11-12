
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Literal


logger = logging.getLogger("finsight.tools")


@dataclass(frozen=True)
class ToolExecutionEvent:
    tool_call_id: str
    investigation_id: str
    agent_id: str
    tool_name: str
    status: Literal["SUCCESS", "FAILED", "TIMEOUT"]
    attempt_count: int
    duration_ms: float
    timestamp: str
    error_type: str | None = None


class ToolTelemetry:
    """
    Records structured tool execution events.

    In-memory storage is for development and testing.
    """

    def __init__(self):
        self._events: list[ToolExecutionEvent] = []
        self._lock = Lock()

    def record(self, event: ToolExecutionEvent) -> None:
        with self._lock:
            self._events.append(event)

        logger.info(json.dumps(asdict(event)))

    def get_events(self) -> list[ToolExecutionEvent]:
        with self._lock:
            return list(self._events)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
