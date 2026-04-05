"""Timestamps: UTC for transcript; local TZ for diary lines and calendar-day paths."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_iso_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def local_iso_ts() -> str:
    return datetime.now().astimezone().isoformat()


def local_date_str() -> str:
    return datetime.now().astimezone().date().isoformat()
