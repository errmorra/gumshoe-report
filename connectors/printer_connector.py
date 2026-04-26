"""
Printer Connector — fetches print-job records from the print management server.

Live mode  : calls PaperCut / PrintAudit / CUPS REST API
Mock mode  : returns synthetic print-job records
"""

import os
import random
import requests
from datetime import datetime, timedelta


class PrinterConnector:
    """Fetches print-job metadata (document name, page count, printer)."""

    PRINT_API_BASE = os.getenv("PRINT_API_BASE", "https://printmgr.internal/api/v1")
    PRINT_API_KEY  = os.getenv("PRINT_API_KEY",  "CHANGEME")

    def __init__(self, mock: bool = True):
        self.mock = mock

    def fetch(self, username: str, since: datetime) -> list[dict]:
        if self.mock:
            return self._mock_data(username, since)
        return self._live_fetch(username, since)

    # ── live ──────────────────────────────────────────────────────────────────
    def _live_fetch(self, username: str, since: datetime) -> list[dict]:
        url = f"{self.PRINT_API_BASE}/jobs"
        params = {"username": username, "from_date": since.isoformat()}
        headers = {"X-API-Key": self.PRINT_API_KEY}
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            return [self._normalise(e) for e in resp.json().get("jobs", [])]
        except requests.RequestException as exc:
            print(f"[Printer] API error: {exc}")
            return []

    @staticmethod
    def _normalise(raw: dict) -> dict:
        return {
            "timestamp":     raw.get("submitted_at", ""),
            "printer":       raw.get("printer_name", "UNKNOWN"),
            "document_name": raw.get("document", raw.get("job_name", "Unnamed")),
            "pages":         int(raw.get("total_pages", 0)),
            "copies":        int(raw.get("copies", 1)),
        }

    # ── mock ──────────────────────────────────────────────────────────────────
    def _mock_data(self, username: str, since: datetime) -> list[dict]:
        random.seed(hash(username + "print") % 2**31)

        jobs = [
            # (hour, min, printer, document, pages, copies)
            (9,  10, "HP-LaserJet-FL4",  "Sprint-42-Planning.docx",          4,  1),
            (10, 33, "HP-LaserJet-FL4",  "Meeting-Agenda-Oct.docx",          2,  1),
            # Suspicious bulk print jobs
            (14, 5,  "HP-LaserJet-FL1",  "Customer_Database_Export_FULL.pdf", 312, 1),
            (14, 22, "HP-LaserJet-FL1",  "SourceCode_Repository_Dump.pdf",   145, 2),
            (14, 55, "HP-LaserJet-FL1",  "Employee_SSN_Records_2024.pdf",     88, 1),
            # After-hours print
            (23, 10, "HP-LaserJet-FL4",  "Confidential_IP_Transfer.pdf",      55, 3),
        ]

        events = []
        for hour, minute, printer, doc, pages, copies in jobs:
            t = since.replace(hour=hour, minute=minute,
                              second=random.randint(0, 59), microsecond=0)
            events.append({
                "timestamp":     t.strftime("%Y-%m-%d %H:%M:%S"),
                "printer":       printer,
                "document_name": doc,
                "pages":         pages,
                "copies":        copies,
            })

        return sorted(events, key=lambda x: x["timestamp"])
