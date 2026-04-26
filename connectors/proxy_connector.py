"""
Proxy Connector — fetches web browsing history from the corporate proxy / CASB.

Live mode  : calls your proxy/CASB REST API (configure via env vars)
Mock mode  : returns a realistic synthetic dataset for the target user
"""

import os
import random
import requests
from datetime import datetime, timedelta


class ProxyConnector:
    """Fetches web proxy events (URLs visited, data transferred)."""

    PROXY_API_BASE = os.getenv("PROXY_API_BASE", "https://proxy.internal/api/v2")
    PROXY_API_KEY  = os.getenv("PROXY_API_KEY",  "CHANGEME")

    def __init__(self, mock: bool = True):
        self.mock = mock

    def fetch(self, username: str, since: datetime) -> list[dict]:
        if self.mock:
            return self._mock_data(username, since)
        return self._live_fetch(username, since)

    # ── live ──────────────────────────────────────────────────────────────────
    def _live_fetch(self, username: str, since: datetime) -> list[dict]:
        url = f"{self.PROXY_API_BASE}/logs"
        params = {"user": username, "from": since.isoformat(), "limit": 1000}
        headers = {"Authorization": f"Bearer {self.PROXY_API_KEY}"}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            return [self._normalise(e) for e in resp.json().get("records", [])]
        except requests.RequestException as exc:
            print(f"[Proxy] API error: {exc}")
            return []

    @staticmethod
    def _normalise(raw: dict) -> dict:
        return {
            "timestamp":          raw.get("time", ""),
            "domain":             raw.get("host", raw.get("domain", "")),
            "category":           raw.get("category", "Uncategorized"),
            "bytes_transferred":  int(raw.get("bytes", 0)),
        }

    # ── mock ──────────────────────────────────────────────────────────────────
    def _mock_data(self, username: str, since: datetime) -> list[dict]:
        random.seed(hash(username + "proxy") % 2**31)

        # (domain, category, typical_bytes)
        normal_sites = [
            ("confluence.internal",     "Business",      45_000),
            ("jira.internal",           "Business",      32_000),
            ("mail.google.com",         "Email",         12_000),
            ("docs.google.com",         "Productivity",  25_000),
            ("stackoverflow.com",       "Developer",     18_000),
            ("slack.com",               "Collaboration", 55_000),
            ("github.com",              "Developer",     40_000),
            ("news.bbc.com",            "News",           8_000),
        ]
        suspicious_sites = [
            ("mega.nz",                  "Cloud Storage",  250_000_000),  # huge upload!
            ("tor2web.org",              "Anonymizer",       4_000),
            ("pastebin.com",             "File Sharing",    12_000),
            ("protonmail.com",           "Email",           15_000),
            ("wetransfer.com",           "File Sharing",   185_000_000),  # large transfer
        ]

        events = []
        t = since + timedelta(hours=1)

        for domain, cat, b in normal_sites:
            t += timedelta(minutes=random.randint(20, 75))
            events.append({
                "timestamp":         t.strftime("%Y-%m-%d %H:%M:%S"),
                "domain":            domain,
                "category":          cat,
                "bytes_transferred": b + random.randint(-5000, 5000),
            })

        # Add suspicious browsing in the afternoon
        for domain, cat, b in suspicious_sites:
            t += timedelta(minutes=random.randint(10, 30))
            events.append({
                "timestamp":         t.strftime("%Y-%m-%d %H:%M:%S"),
                "domain":            domain,
                "category":          cat,
                "bytes_transferred": b,
            })

        return sorted(events, key=lambda x: x["timestamp"])
