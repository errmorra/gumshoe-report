"""
Badge Connector — fetches physical access events from the access control system.

Live mode  : calls the badge/access-control REST API
Mock mode  : returns realistic synthetic events
"""

import os
import random
import requests
from datetime import datetime, timedelta


class BadgeConnector:
    """Fetches badge swipe events (entry/exit, door access)."""

    BADGE_API_BASE = os.getenv("BADGE_API_BASE", "https://access.internal/api/v1")
    BADGE_API_KEY  = os.getenv("BADGE_API_KEY",  "CHANGEME")

    def __init__(self, mock: bool = True):
        self.mock = mock

    def fetch(self, username: str, since: datetime) -> list[dict]:
        if self.mock:
            return self._mock_data(username, since)
        return self._live_fetch(username, since)

    # ── live ──────────────────────────────────────────────────────────────────
    def _live_fetch(self, username: str, since: datetime) -> list[dict]:
        url = f"{self.BADGE_API_BASE}/access-events"
        params = {"employee_id": username, "since": since.isoformat()}
        headers = {"X-API-Key": self.BADGE_API_KEY}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            return [self._normalise(e) for e in resp.json().get("events", [])]
        except requests.RequestException as exc:
            print(f"[Badge] API error: {exc}")
            return []

    @staticmethod
    def _normalise(raw: dict) -> dict:
        return {
            "timestamp": raw.get("event_time", ""),
            "location":  raw.get("door_name", raw.get("location", "UNKNOWN")),
            "direction": "ENTRY" if raw.get("direction") in ("in", "entry") else "EXIT",
            "result":    "GRANTED" if raw.get("access_result") in ("granted", "ok") else "DENIED",
        }

    # ── mock ──────────────────────────────────────────────────────────────────
    def _mock_data(self, username: str, since: datetime) -> list[dict]:
        random.seed(hash(username + "badge") % 2**31)

        events = []
        t = since.replace(hour=8, minute=22, second=0, microsecond=0)

        schedule = [
            # (hour, min, location, direction, result)
            (8, 22,  "Main Lobby — Turnstile A",          "ENTRY",  "GRANTED"),
            (8, 24,  "Floor 4 — Engineering Suite",        "ENTRY",  "GRANTED"),
            (12, 5,  "Floor 4 — Engineering Suite",        "EXIT",   "GRANTED"),
            (12, 6,  "Cafeteria — Level 1",                "ENTRY",  "GRANTED"),
            (12, 58, "Cafeteria — Level 1",                "EXIT",   "GRANTED"),
            (13, 0,  "Floor 4 — Engineering Suite",        "ENTRY",  "GRANTED"),
            # Suspicious: tried to access restricted server room
            (15, 34, "Floor 3 — SERVER ROOM (RESTRICTED)", "ENTRY",  "DENIED"),
            (15, 35, "Floor 3 — SERVER ROOM (RESTRICTED)", "ENTRY",  "DENIED"),
            # After-hours re-entry (very late)
            (22, 47, "Main Lobby — Turnstile A",           "ENTRY",  "GRANTED"),
            (22, 49, "Floor 4 — Engineering Suite",        "ENTRY",  "GRANTED"),
            (23, 58, "Main Lobby — Turnstile A",           "EXIT",   "GRANTED"),
        ]

        for hour, minute, loc, direction, result in schedule:
            t = since.replace(hour=hour, minute=minute, second=random.randint(0, 59), microsecond=0)
            events.append({
                "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
                "location":  loc,
                "direction": direction,
                "result":    result,
            })

        return sorted(events, key=lambda x: x["timestamp"])
