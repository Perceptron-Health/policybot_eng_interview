import json
import time
from typing import Any, Dict, List


class Metrics:
    """
    Tiny in-process metrics. Great for pairing.
    Candidates can extend to:
      - count by strategy
      - track top inferred codes
      - track error rate
      - latency by strategy
    """

    def __init__(self) -> None:
        self.counters: Dict[str, int] = {}
        self.timings_ms: Dict[str, List[float]] = {}

    def inc(self, key: str, n: int = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + n

    def observe_ms(self, key: str, ms: float) -> None:
        self.timings_ms.setdefault(key, []).append(ms)

    def snapshot(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"counters": dict(self.counters), "timings_ms": {}}
        for k, vals in self.timings_ms.items():
            if not vals:
                continue
            out["timings_ms"][k] = {
                "count": len(vals),
                "avg_ms": sum(vals) / len(vals),
                "max_ms": max(vals),
            }
        return out


def log_event(event: Dict[str, Any]) -> None:
    """
    Structured logs to stdout.
    Pairing ideas:
      - standardize event names
      - include request_id, strategy, run_id
      - log errors with consistent shape
    """
    print(json.dumps(event, separators=(",", ":"), default=str))


class Timer:
    def __init__(self) -> None:
        self._t0 = time.perf_counter()

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self._t0) * 1000.0
