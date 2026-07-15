from __future__ import annotations

from enum import Enum


class BotState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


def compute_runtime_seconds(start_time, total_paused_duration=0.0, pause_started_at=None, state=BotState.STOPPED, now=None):
    if not start_time:
        return 0.0
    if now is None:
        import time
        now = time.time()

    runtime = max(0.0, now - start_time - float(total_paused_duration or 0.0))
    if state == BotState.PAUSED and pause_started_at is not None:
        runtime -= max(0.0, now - pause_started_at)
    return max(0.0, runtime)
