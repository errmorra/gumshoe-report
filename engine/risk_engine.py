"""
Risk Engine — scores a user's 24-hour activity and produces an indicator list.

Scoring bands:
  0–24  →  LOW
  25–49 →  MEDIUM
  50–74 →  HIGH
  75+   →  CRITICAL
"""

from datetime import datetime


class RiskEngine:
    """
    Stateless rule-based risk scorer.
    Each rule adds points to the total score (capped at 100).
    """

    AFTER_HOURS_START = 20   # 8 pm
    AFTER_HOURS_END   = 6    # 6 am

    # Categories considered high-risk for data exfiltration
    EXFIL_CATEGORIES  = {"Cloud Storage", "File Sharing", "Anonymizer", "Data Exfil"}
    # Restricted location keywords
    RESTRICTED_ROOMS  = {"SERVER ROOM", "RESTRICTED", "DATA CENTER", "EXECUTIVE"}

    def score(
        self,
        username: str,
        ad_data:      list[dict],
        proxy_data:   list[dict],
        badge_data:   list[dict],
        printer_data: list[dict],
    ) -> dict:
        indicators = []
        total = 0

        # ── AD / Login rules ──────────────────────────────────────────────────
        failed_logins = [e for e in ad_data if e["result"] == "FAILURE"]
        if len(failed_logins) >= 3:
            total += 20
            indicators.append({
                "category":    "Authentication",
                "severity":    "HIGH",
                "description": f"{len(failed_logins)} failed login attempts in 24 hours — possible brute-force.",
            })
        elif len(failed_logins) >= 1:
            total += 8
            indicators.append({
                "category":    "Authentication",
                "severity":    "MEDIUM",
                "description": f"{len(failed_logins)} failed login attempt(s) detected.",
            })

        no_mfa = [e for e in ad_data if not e.get("mfa_used") and e["result"] == "SUCCESS"]
        if no_mfa:
            total += 15
            indicators.append({
                "category":    "Authentication",
                "severity":    "HIGH",
                "description": f"{len(no_mfa)} successful login(s) completed WITHOUT multi-factor authentication.",
            })

        external_logins = [e for e in ad_data
                           if e["result"] == "SUCCESS"
                           and not e["source_ip"].startswith(("10.", "172.", "192."))]
        if external_logins:
            total += 20
            indicators.append({
                "category":    "Authentication",
                "severity":    "HIGH",
                "description": f"Login from external IP(s): {', '.join(e['source_ip'] for e in external_logins)}.",
            })

        ah_logins = [e for e in ad_data if self._after_hours(e["timestamp"]) and e["result"] == "SUCCESS"]
        if ah_logins:
            total += 10
            indicators.append({
                "category":    "Temporal",
                "severity":    "MEDIUM",
                "description": f"{len(ah_logins)} login(s) outside business hours (before 6 AM or after 8 PM).",
            })

        # ── Proxy / Web rules ─────────────────────────────────────────────────
        exfil_sites = [e for e in proxy_data if e["category"] in self.EXFIL_CATEGORIES]
        if exfil_sites:
            total += 15
            sites = ", ".join(e["domain"] for e in exfil_sites)
            indicators.append({
                "category":    "Web Activity",
                "severity":    "HIGH",
                "description": f"Visited high-risk exfiltration-category site(s): {sites}.",
            })

        large_uploads = [e for e in proxy_data if e["bytes_transferred"] > 50_000_000]
        if large_uploads:
            total += 25
            total_mb = sum(e["bytes_transferred"] for e in large_uploads) / 1_048_576
            indicators.append({
                "category":    "Data Transfer",
                "severity":    "HIGH",
                "description": f"Outbound data spike: {total_mb:,.0f} MB transferred to web (threshold: 50 MB).",
            })

        # ── Badge / Physical rules ────────────────────────────────────────────
        denied_access = [e for e in badge_data if e["result"] == "DENIED"]
        if denied_access:
            total += 15
            locs = ", ".join(e["location"] for e in denied_access)
            indicators.append({
                "category":    "Physical Access",
                "severity":    "HIGH",
                "description": f"Attempted access to restricted area(s): {locs}.",
            })

        restricted_attempts = [e for e in badge_data
                                if any(kw in e["location"].upper() for kw in self.RESTRICTED_ROOMS)]
        if restricted_attempts:
            total += 5  # extra penalty on top of denied_access
            indicators.append({
                "category":    "Physical Access",
                "severity":    "MEDIUM",
                "description": "Badge swipe attempted at a classified/restricted location.",
            })

        ah_badge = [e for e in badge_data if self._after_hours(e["timestamp"])]
        if ah_badge:
            total += 10
            indicators.append({
                "category":    "Physical Access",
                "severity":    "MEDIUM",
                "description": f"{len(ah_badge)} badge event(s) outside standard business hours.",
            })

        # ── Printing rules ────────────────────────────────────────────────────
        sensitive_kw = ("confidential", "classified", "employee", "ssn", "database",
                        "export", "source", "ip_transfer", "salary", "customer")
        sensitive_prints = [e for e in printer_data
                            if any(kw in e["document_name"].lower() for kw in sensitive_kw)]
        if sensitive_prints:
            total += 20
            docs = ", ".join(e["document_name"] for e in sensitive_prints)
            indicators.append({
                "category":    "Printing",
                "severity":    "HIGH",
                "description": f"Printed potentially sensitive document(s): {docs}.",
            })

        bulk_pages = sum(e["pages"] * e.get("copies", 1) for e in printer_data)
        if bulk_pages > 200:
            total += 15
            indicators.append({
                "category":    "Printing",
                "severity":    "MEDIUM",
                "description": f"Unusually high print volume: {bulk_pages} total pages (threshold: 200).",
            })

        ah_prints = [e for e in printer_data if self._after_hours(e["timestamp"])]
        if ah_prints:
            total += 10
            indicators.append({
                "category":    "Temporal",
                "severity":    "MEDIUM",
                "description": f"{len(ah_prints)} print job(s) submitted outside business hours.",
            })

        # ── Finalise ──────────────────────────────────────────────────────────
        total = min(total, 100)
        level = (
            "CRITICAL" if total >= 75 else
            "HIGH"     if total >= 50 else
            "MEDIUM"   if total >= 25 else
            "LOW"
        )

        return {
            "username":    username,
            "risk_score":  total,
            "risk_level":  level,
            "indicators":  indicators,
            "generated":   datetime.now().isoformat(),
        }

    # ── helpers ───────────────────────────────────────────────────────────────
    def _after_hours(self, timestamp_str: str) -> bool:
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            return dt.hour >= self.AFTER_HOURS_START or dt.hour < self.AFTER_HOURS_END
        except ValueError:
            return False
