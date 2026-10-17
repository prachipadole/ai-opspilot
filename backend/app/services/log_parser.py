"""
log_parser.py – Parse raw log strings into structured dicts.
Supports: JSON logs, Syslog-style, plain key=value, and free-text.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


# Syslog-style:  Oct 17 09:23:11 hostname service[pid]: message
_SYSLOG_RE = re.compile(
    r"(?P<month>\w{3})\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<service>\S+?)(?:\[(?P<pid>\d+)\])?\s*:\s*(?P<message>.*)"
)
# Apache/Nginx combined log
_HTTP_RE = re.compile(
    r'(?P<ip>[\d.]+)\s+-\s+-\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\w+)\s+(?P<path>\S+)'
    r'\s+HTTP/\d\.\d"\s+(?P<status>\d{3})\s+(?P<bytes>\d+)'
)
_LEVEL_RE = re.compile(r'\b(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL|FATAL)\b', re.I)


def _extract_level(text: str) -> str:
    m = _LEVEL_RE.search(text)
    return m.group(1).upper() if m else "INFO"


def parse_log_line(raw: str) -> Dict[str, Any]:
    """
    Parse a single log line.  Returns a dict with at least:
    { service, level, message, timestamp, raw }
    """
    raw = raw.strip()
    result: Dict[str, Any] = {
        "service": None,
        "level": "INFO",
        "message": raw,
        "timestamp": datetime.utcnow().isoformat(),
        "raw": {},
    }

    # 1. JSON log
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            result["service"]   = parsed.get("service") or parsed.get("logger")
            result["level"]     = (parsed.get("level") or parsed.get("severity") or "INFO").upper()
            result["message"]   = parsed.get("message") or parsed.get("msg") or raw
            result["timestamp"] = parsed.get("timestamp") or parsed.get("time") or result["timestamp"]
            result["raw"]       = parsed
            return result
        except json.JSONDecodeError:
            pass

    # 2. Syslog
    m = _SYSLOG_RE.match(raw)
    if m:
        result["service"] = m.group("service")
        result["message"] = m.group("message")
        result["level"]   = _extract_level(m.group("message"))
        result["raw"]     = m.groupdict()
        return result

    # 3. HTTP access log
    m = _HTTP_RE.match(raw)
    if m:
        status = int(m.group("status"))
        result["service"] = "http"
        result["level"]   = "ERROR" if status >= 500 else "WARNING" if status >= 400 else "INFO"
        result["message"] = f'{m.group("method")} {m.group("path")} → {status}'
        result["raw"]     = m.groupdict()
        return result

    # 4. Fallback – extract level from text
    result["level"] = _extract_level(raw)
    return result


def parse_logs(raw_logs: List[str]) -> List[Dict[str, Any]]:
    """Parse a list of raw log lines."""
    parsed = []
    for line in raw_logs:
        if not line.strip():
            continue
        try:
            parsed.append(parse_log_line(line))
        except Exception as exc:
            logger.warning(f"Failed to parse log line: {exc}")
    return parsed


def extract_metrics(parsed_logs: List[Dict[str, Any]]) -> Dict[str, List[float]]:
    """
    Extract numeric metrics from parsed logs for anomaly detection.
    Returns: { metric_name: [values ...] }
    """
    metrics: Dict[str, List[float]] = {
        "error_rate":       [],
        "response_time_ms": [],
        "status_5xx":       [],
    }

    for entry in parsed_logs:
        raw = entry.get("raw", {})

        if entry.get("level") in ("ERROR", "CRITICAL", "FATAL"):
            metrics["error_rate"].append(1.0)
        else:
            metrics["error_rate"].append(0.0)

        # Response time from JSON log
        for key in ("response_time", "duration_ms", "latency_ms"):
            if key in raw:
                try:
                    metrics["response_time_ms"].append(float(raw[key]))
                except (TypeError, ValueError):
                    pass

        # HTTP status
        if "status" in raw:
            try:
                code = int(raw["status"])
                metrics["status_5xx"].append(1.0 if code >= 500 else 0.0)
            except (TypeError, ValueError):
                pass

    return {k: v for k, v in metrics.items() if v}
