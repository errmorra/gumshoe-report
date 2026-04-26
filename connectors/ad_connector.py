"""
AD Connector — fetches login events from Active Directory / SIEM API.

Live mode  : calls your org's AD/SIEM REST endpoint (configure via env vars)
Mock mode  : returns a realistic synthetic dataset for the target user
"""

import os
import random
import requests
from datetime import datetime, timedelta


class ADConnector:
    """Fetches user login events from Active Directory / SIEM."""

    AD_API_BASE = os.getenv("AD_API_BASE", "https://siem.internal/api/v1")
    AD_API_KEY  = os.getenv("AD_API_KEY",  "CHANGEME")

    def __init__(self, mock: bool = True):
        self.mock = mock

    # ── public ────────────────────────────────────────────────────────────────
    def fetch(self, username: str, since: datetime) -> list[dict]:
        """Return list of login event dicts for *username* since *since*."""
        if self.mock:
            return self._mock_data(username, since)
        return self._live_fetch(username, since)

    # ── live API ──────────────────────────────────────────────────────────────
    def _live_fetch(self, username: str, since: datetime) -> list[dict]:
        """
        Example call against a SIEM / AD event log API.
        Adapt the endpoint, headers, and JSON parsing to your environment.
        """
        url = f"{self.AD_API_BASE}/events/logins"
        params = {
            "user":       username,
            "since":      since.isoformat(),
            "event_type": "logon,logoff,failed_logon",
            "limit":      500,
        }
        headers = {"X-API-Key": self.AD_API_KEY, "Accept": "application/json"}

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            raw = resp.json().get("events", [])
            return [self._normalise(e) for e in raw]
        except requests.RequestException as exc:
            print(f"[AD] API error: {exc}")
            return []

    @staticmethod
    def _normalise(raw: dict) -> dict:
        """Map vendor-specific field names to our schema."""
        return {
            "timestamp":   raw.get("event_time", raw.get("timestamp", "")),
            "workstation": raw.get("computer_name", raw.get("workstation", "UNKNOWN")),
            "source_ip":   raw.get("ip_address", raw.get("source_ip", "0.0.0.0")),
            "result":      "SUCCESS" if raw.get("logon_result") in ("0x0", "success") else "FAILURE",
            "mfa_used":    raw.get("mfa_method") not in (None, "", "none"),
        }

    # ── mock data ─────────────────────────────────────────────────────────────
    def _mock_data(self, username: str, since: datetime) -> list[dict]:
        """Realistic synthetic login events (seeded for reproducibility)."""
        random.seed(hash(username) % 2**31)
        workstations = [f"WKS-{username[:4].upper()}-01", "LAPTOP-CORP-088", "RDP-SERVER-02"]
        ips_internal = ["10.0.1.42", "10.0.2.17", "10.10.0.5"]
        ips_external = ["185.220.101.45", "91.108.56.12"]  # suspicious

        events = []
        now = datetime.now()

        # Normal morning login
        t = since.replace(hour=8, minute=30, second=0, microsecond=0) + timedelta(minutes=random.randint(-15, 15))
        events.append({
            "timestamp":   t.strftime("%Y-%m-%d %H:%M:%S"),
            "workstation": workstations[0],
            "source_ip":   ips_internal[0],
            "result":      "SUCCESS",
            "mfa_used":    True,
        })

        # One failed login attempt (wrong password?)
        t += timedelta(minutes=random.randint(30, 90))
        events.append({
            "timestamp":   t.strftime("%Y-%m-%d %H:%M:%S"),
            "workstation": workstations[2],
            "source_ip":   ips_internal[1],
            "result":      "FAILURE",
            "mfa_used":    False,
        })

        # Suspicious after-hours login from external IP
        t = now.replace(hour=23, minute=17, second=0, microsecond=0) - timedelta(days=0)
        events.append({
            "timestamp":   t.strftime("%Y-%m-%d %H:%M:%S"),
            "workstation": "RDP-SERVER-02",
            "source_ip":   ips_external[0],
            "result":      "SUCCESS",
            "mfa_used":    False,  # no MFA — high risk
        })

        # Normal afternoon logout
        t = since.replace(hour=17, minute=45, second=0, microsecond=0)
        events.append({
            "timestamp":   t.strftime("%Y-%m-%d %H:%M:%S"),
            "workstation": workstations[0],
            "source_ip":   ips_internal[0],
            "result":      "SUCCESS",
            "mfa_used":    True,
        })

        return sorted(events, key=lambda x: x["timestamp"])
