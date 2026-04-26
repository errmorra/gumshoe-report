"""
Unit tests for the GumShoe risk scoring engine.

Run with pytest (recommended):
    pytest tests/ -v

Or with the stdlib runner (no install needed):
    python3 tests/test_risk_engine.py
"""

import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from engine.risk_engine import RiskEngine

NOW    = datetime.now()
engine = RiskEngine()

def _login(result="SUCCESS", mfa=True, ip="10.0.1.1", hour=9):
    t = NOW.replace(hour=hour, minute=0, second=0, microsecond=0)
    return {"timestamp": t.strftime("%Y-%m-%d %H:%M:%S"), "workstation": "WKS-TEST",
            "source_ip": ip, "result": result, "mfa_used": mfa}

def _proxy(domain="example.com", category="Business", mb=1):
    return {"timestamp": NOW.strftime("%Y-%m-%d %H:%M:%S"), "domain": domain,
            "category": category, "bytes_transferred": mb * 1_048_576}

def _badge(location="Floor 1 — Office", direction="ENTRY", result="GRANTED", hour=9):
    t = NOW.replace(hour=hour, minute=0, second=0, microsecond=0)
    return {"timestamp": t.strftime("%Y-%m-%d %H:%M:%S"), "location": location,
            "direction": direction, "result": result}

def _print_job(doc="report.pdf", pages=5, copies=1, hour=10):
    t = NOW.replace(hour=hour, minute=0, second=0, microsecond=0)
    return {"timestamp": t.strftime("%Y-%m-%d %H:%M:%S"), "printer": "HP-LaserJet",
            "document_name": doc, "pages": pages, "copies": copies}

def sc(*args):
    return engine.score(*args)["risk_score"]


class TestAuthRules(unittest.TestCase):
    def test_clean_user_scores_low(self):
        r = engine.score("alice", [_login()], [], [], [])
        self.assertEqual(r["risk_level"], "LOW")
        self.assertLess(r["risk_score"], 25)

    def test_no_mfa_adds_15(self):
        self.assertEqual(sc("u", [_login(mfa=False)], [], [], []) - sc("u", [_login(mfa=True)], [], [], []), 15)

    def test_external_ip_adds_20(self):
        self.assertEqual(sc("u", [_login(ip="185.220.101.45")], [], [], []) - sc("u", [_login(ip="10.0.1.1")], [], [], []), 20)

    def test_single_failed_login_adds_8(self):
        self.assertEqual(sc("u", [_login(result="FAILURE")], [], [], []) - sc("u", [], [], [], []), 8)

    def test_three_failed_logins_adds_20(self):
        self.assertEqual(sc("u", [_login(result="FAILURE")] * 3, [], [], []) - sc("u", [], [], [], []), 20)

    def test_after_hours_login_adds_10(self):
        self.assertEqual(sc("u", [_login(hour=23)], [], [], []) - sc("u", [_login(hour=10)], [], [], []), 10)


class TestProxyRules(unittest.TestCase):
    def test_exfil_category_adds_15(self):
        self.assertEqual(sc("u", [], [_proxy(category="Anonymizer")], [], []) - sc("u", [], [_proxy(category="Business")], [], []), 15)

    def test_large_upload_adds_25(self):
        self.assertEqual(sc("u", [], [_proxy(mb=100)], [], []) - sc("u", [], [_proxy(mb=10)], [], []), 25)

    def test_score_capped_at_100(self):
        r = engine.score("u",
            [_login(mfa=False, ip="185.1.2.3", result="FAILURE")] * 5,
            [_proxy(category="Anonymizer", mb=500)],
            [_badge(location="SERVER ROOM (RESTRICTED)", result="DENIED")],
            [_print_job(doc="employee_ssn.pdf", pages=500)])
        self.assertEqual(r["risk_score"], 100)
        self.assertEqual(r["risk_level"], "CRITICAL")


class TestBadgeRules(unittest.TestCase):
    def test_denied_access_adds_15(self):
        self.assertEqual(sc("u", [], [], [_badge(result="DENIED")], []) - sc("u", [], [], [_badge(result="GRANTED")], []), 15)

    def test_restricted_location_adds_extra(self):
        normal     = sc("u", [], [], [_badge(result="DENIED", location="Floor 1")], [])
        restricted = sc("u", [], [], [_badge(result="DENIED", location="SERVER ROOM (RESTRICTED)")], [])
        self.assertGreater(restricted, normal)

    def test_after_hours_badge_adds_10(self):
        self.assertEqual(sc("u", [], [], [_badge(hour=23)], []) - sc("u", [], [], [_badge(hour=10)], []), 10)


class TestPrintingRules(unittest.TestCase):
    def test_sensitive_document_adds_20(self):
        self.assertEqual(
            sc("u", [], [], [], [_print_job(doc="employee_ssn_export.pdf")]) -
            sc("u", [], [], [], [_print_job(doc="agenda.pdf")]), 20)

    def test_bulk_print_adds_15(self):
        self.assertEqual(
            sc("u", [], [], [], [_print_job(pages=201)]) -
            sc("u", [], [], [], [_print_job(pages=10)]), 15)

    def test_after_hours_print_adds_10(self):
        self.assertEqual(
            sc("u", [], [], [], [_print_job(hour=23)]) -
            sc("u", [], [], [], [_print_job(hour=10)]), 10)


class TestIndicatorOutput(unittest.TestCase):
    def test_indicators_have_required_keys(self):
        r = engine.score("u", [_login(mfa=False)], [], [], [])
        for ind in r["indicators"]:
            self.assertIn("category",    ind)
            self.assertIn("severity",    ind)
            self.assertIn("description", ind)

    def test_clean_user_has_no_indicators(self):
        r = engine.score("clean", [_login()], [], [], [])
        self.assertEqual(r["indicators"], [])

    def test_zero_score_is_low(self):
        r = engine.score("u", [], [], [], [])
        self.assertEqual(r["risk_level"], "LOW")
        self.assertEqual(r["risk_score"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
