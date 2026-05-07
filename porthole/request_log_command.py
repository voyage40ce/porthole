"""CLI command: ``porthole request-log`` — display recent proxied requests."""
from __future__ import annotations

from typing import List, Optional

from porthole.request_log import RequestLog, RequestLogEntry, get_request_log

_COL_SERVICE = 20
_COL_METHOD = 6
_COL_PATH = 40
_COL_STATUS = 6
_COL_DURATION = 10


def _header() -> str:
    return (
        f"{'TIMESTAMP':10s}  {'SERVICE':{_COL_SERVICE}s}  {'METHOD':{_COL_METHOD}s}"
        f"  {'PATH':{_COL_PATH}s}  {'STATUS':{_COL_STATUS}s}  {'DURATION_MS':>{_COL_DURATION}s}"
    )


def _row(entry: RequestLogEntry) -> str:
    ts = entry.timestamp.strftime("%H:%M:%S")
    return (
        f"{ts:10s}  {entry.service:{_COL_SERVICE}s}  {entry.method:{_COL_METHOD}s}"
        f"  {entry.path:{_COL_PATH}s}  {entry.status_code!s:{_COL_STATUS}s}"
        f"  {entry.duration_ms:>{_COL_DURATION}.1f}"
    )


def run_request_log(
    n: Optional[int] = 50,
    service_filter: Optional[str] = None,
    status_filter: Optional[int] = None,
    log: Optional[RequestLog] = None,
) -> None:
    """Print recent request log entries to stdout.

    Parameters
    ----------
    n:
        Maximum number of entries to display (``None`` = all).
    service_filter:
        When set, only show entries whose service name matches.
    status_filter:
        When set, only show entries with this HTTP status code.
    log:
        Override the global :class:`RequestLog` (useful in tests).
    """
    log = log or get_request_log()
    entries: List[RequestLogEntry] = log.recent(n)

    if service_filter:
        entries = [e for e in entries if e.service == service_filter]
    if status_filter is not None:
        entries = [e for e in entries if e.status_code == status_filter]

    if not entries:
        print("No request log entries found.")
        return

    print(_header())
    print("-" * (10 + 2 + _COL_SERVICE + 2 + _COL_METHOD + 2 + _COL_PATH + 2 + _COL_STATUS + 2 + _COL_DURATION))
    for entry in entries:
        print(_row(entry))
