"""
DishIQ Phase 14 — Operational Metrics Collector

Thread-safe, lightweight, bounded in-memory metrics tracker.
Tracks request counts, latency, HTTP status code distributions,
database errors, and external provider failures without external infrastructure.
"""

import time
import threading
from typing import Dict, Any


class MetricsCollector:
    """
    In-memory metrics collector with bounded, low-cardinality keys.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._requests_total = 0
        self._requests_by_status = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
        self._requests_by_method = {"GET": 0, "POST": 0, "PUT": 0, "PATCH": 0, "DELETE": 0, "OTHER": 0}
        self._total_duration_ms = 0.0
        self._database_errors_total = 0
        self._external_provider_failures_total = 0

    def record_request(self, method: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self._requests_total += 1
            self._total_duration_ms += duration_ms

            # Bounded method classification
            m = method.upper()
            if m in self._requests_by_method:
                self._requests_by_method[m] += 1
            else:
                self._requests_by_method["OTHER"] += 1

            # Bounded status code category
            if 200 <= status_code < 300:
                self._requests_by_status["2xx"] += 1
            elif 300 <= status_code < 400:
                self._requests_by_status["3xx"] += 1
            elif 400 <= status_code < 500:
                self._requests_by_status["4xx"] += 1
            elif status_code >= 500:
                self._requests_by_status["5xx"] += 1

    def record_db_error(self) -> None:
        with self._lock:
            self._database_errors_total += 1

    def record_provider_failure(self) -> None:
        with self._lock:
            self._external_provider_failures_total += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime_seconds = round(time.time() - self._start_time, 1)
            total = self._requests_total
            avg_latency = round(self._total_duration_ms / total, 2) if total > 0 else 0.0
            error_count = self._requests_by_status["4xx"] + self._requests_by_status["5xx"]
            error_rate = round((error_count / total) * 100, 2) if total > 0 else 0.0

            return {
                "uptime_seconds": uptime_seconds,
                "requests_total": total,
                "requests_by_status": dict(self._requests_by_status),
                "requests_by_method": dict(self._requests_by_method),
                "error_rate_percent": error_rate,
                "average_latency_ms": avg_latency,
                "database_errors_total": self._database_errors_total,
                "external_provider_failures_total": self._external_provider_failures_total,
            }

    def reset(self) -> None:
        """Reset counters (used primarily for test isolation)."""
        with self._lock:
            self._requests_total = 0
            self._requests_by_status = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
            self._requests_by_method = {"GET": 0, "POST": 0, "PUT": 0, "PATCH": 0, "DELETE": 0, "OTHER": 0}
            self._total_duration_ms = 0.0
            self._database_errors_total = 0
            self._external_provider_failures_total = 0
            self._start_time = time.time()


# Application singleton
metrics = MetricsCollector()
