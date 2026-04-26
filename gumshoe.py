#!/usr/bin/env python3
"""
=============================================================================
  GUMSHOE REPORT  v1.0
  Automated Insider Threat Triage — 24-Hour User Activity Aggregator
=============================================================================
  Pulls last 24 hours of:  AD Logins | Web Proxy | Badge Swipes | Printing
  Outputs:  Terminal summary (color-coded) + PDF investigation report
=============================================================================
"""

import argparse
import json
import sys
import os
from datetime import datetime, timedelta

from connectors.ad_connector       import ADConnector
from connectors.proxy_connector    import ProxyConnector
from connectors.badge_connector    import BadgeConnector
from connectors.printer_connector  import PrinterConnector
from engine.risk_engine            import RiskEngine
from reports.pdf_report            import generate_pdf_report

# ── ANSI colour helpers ──────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
GREEN   = "\033[92m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
DIM     = "\033[2m"
MAGENTA = "\033[95m"


def banner():
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════════════════════╗
║   🔍  GUMSHOE REPORT  ·  v1.0                                        ║
║       Automated Insider Threat Triage — 24-Hour Activity Aggregator  ║
╚══════════════════════════════════════════════════════════════════════╝{RESET}
""")


def section_header(title: str):
    print(f"\n{CYAN}{BOLD}{'─'*64}{RESET}")
    print(f"{CYAN}{BOLD}  {title}{RESET}")
    print(f"{CYAN}{'─'*64}{RESET}")


def print_logins(logins: list):
    section_header("🔐  ACTIVE DIRECTORY — LOGIN EVENTS")
    if not logins:
        print(f"  {DIM}No login events in the past 24 hours.{RESET}")
        return
    print(f"  {'Timestamp':<22} {'Workstation':<20} {'IP Address':<18} {'Result':<10} {'MFA'}")
    print(f"  {'─'*22} {'─'*20} {'─'*18} {'─'*10} {'─'*5}")
    for e in logins:
        result_col = GREEN if e["result"] == "SUCCESS" else RED
        mfa_col    = GREEN if e.get("mfa_used") else YELLOW
        print(f"  {e['timestamp']:<22} {e['workstation']:<20} {e['source_ip']:<18} "
              f"{result_col}{e['result']:<10}{RESET} "
              f"{mfa_col}{'YES' if e.get('mfa_used') else 'NO'}{RESET}")


def print_proxy(proxy: list):
    section_header("🌐  WEB PROXY — BROWSING HISTORY")
    if not proxy:
        print(f"  {DIM}No proxy events in the past 24 hours.{RESET}")
        return
    print(f"  {'Timestamp':<22} {'Domain':<35} {'Category':<20} {'Bytes':>9}")
    print(f"  {'─'*22} {'─'*35} {'─'*20} {'─'*9}")
    for e in proxy:
        cat_col = RED if e["category"] in ("Malware","Data Exfil","Hacking","Anonymizer") else (
                  YELLOW if e["category"] in ("Cloud Storage","File Sharing","Social Media") else RESET)
        print(f"  {e['timestamp']:<22} {e['domain'][:34]:<35} "
              f"{cat_col}{e['category']:<20}{RESET} {e['bytes_transferred']:>9,}")


def print_badge(badge: list):
    section_header("🏢  PHYSICAL ACCESS — BADGE SWIPES")
    if not badge:
        print(f"  {DIM}No badge swipe events in the past 24 hours.{RESET}")
        return
    print(f"  {'Timestamp':<22} {'Location':<30} {'Direction':<12} {'Result'}")
    print(f"  {'─'*22} {'─'*30} {'─'*12} {'─'*10}")
    for e in badge:
        dir_col = GREEN if e["direction"] == "ENTRY" else CYAN
        res_col = GREEN if e["result"] == "GRANTED" else RED
        print(f"  {e['timestamp']:<22} {e['location']:<30} "
              f"{dir_col}{e['direction']:<12}{RESET} {res_col}{e['result']}{RESET}")


def print_printing(printing: list):
    section_header("🖨️   PRINTING ACTIVITY")
    if not printing:
        print(f"  {DIM}No print jobs in the past 24 hours.{RESET}")
        return
    print(f"  {'Timestamp':<22} {'Printer':<20} {'Document':<35} {'Pages':>6} {'Copies':>7}")
    print(f"  {'─'*22} {'─'*20} {'─'*35} {'─'*6} {'─'*7}")
    for e in printing:
        page_col = RED if e["pages"] * e.get("copies", 1) > 50 else RESET
        print(f"  {e['timestamp']:<22} {e['printer']:<20} {e['document_name'][:34]:<35} "
              f"{page_col}{e['pages']:>6} {e.get('copies',1):>7}{RESET}")


def print_risk_summary(report: dict):
    section_header("⚠️   RISK ASSESSMENT SUMMARY")
    score = report["risk_score"]
    level = report["risk_level"]
    bar_len = min(int(score / 2), 50)
    bar_col = RED if level in ("CRITICAL","HIGH") else (YELLOW if level == "MEDIUM" else GREEN)
    bar = "█" * bar_len + "░" * (50 - bar_len)

    print(f"\n  Overall Risk Score : {bar_col}{BOLD}{score}/100{RESET}  {level}")
    print(f"  {bar_col}{bar}{RESET}\n")

    if report["indicators"]:
        print(f"  {BOLD}Triggered Indicators:{RESET}")
        for ind in report["indicators"]:
            sev_col = RED if ind["severity"] == "HIGH" else YELLOW
            print(f"    {sev_col}▶{RESET}  [{sev_col}{ind['severity']}{RESET}]  {ind['description']}")
    else:
        print(f"  {GREEN}No suspicious indicators detected.{RESET}")


def run_triage(username: str, mock: bool, output_dir: str, dump_json: bool = False):
    banner()
    since = datetime.now() - timedelta(hours=24)
    print(f"  {WHITE}Target User  :{RESET} {BOLD}{username}{RESET}")
    print(f"  {WHITE}Time Window  :{RESET} {since.strftime('%Y-%m-%d %H:%M')}  →  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  {WHITE}Data Mode    :{RESET} {'Simulated (--mock)' if mock else 'Live API'}")

    print(f"\n{DIM}  Querying data sources…{RESET}", end="", flush=True)
    ad_data      = ADConnector(mock=mock).fetch(username, since)
    proxy_data   = ProxyConnector(mock=mock).fetch(username, since)
    badge_data   = BadgeConnector(mock=mock).fetch(username, since)
    printer_data = PrinterConnector(mock=mock).fetch(username, since)
    print(f"\r  {GREEN}✓{RESET} All data sources queried.                    ")

    engine      = RiskEngine()
    risk_report = engine.score(username, ad_data, proxy_data, badge_data, printer_data)

    print_logins(ad_data)
    print_proxy(proxy_data)
    print_badge(badge_data)
    print_printing(printer_data)
    print_risk_summary(risk_report)

    os.makedirs(output_dir, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(output_dir, f"gumshoe_{username}_{ts}.pdf")

    generate_pdf_report(
        username     = username,
        since        = since,
        ad_data      = ad_data,
        proxy_data   = proxy_data,
        badge_data   = badge_data,
        printer_data = printer_data,
        risk_report  = risk_report,
        output_path  = pdf_path,
    )

    if dump_json:
        json_path = pdf_path.replace(".pdf", ".json")
        payload = {
            "username":    username,
            "generated":   datetime.now().isoformat(),
            "risk_score":  risk_report["risk_score"],
            "risk_level":  risk_report["risk_level"],
            "indicators":  risk_report["indicators"],
            "ad_events":   ad_data,
            "proxy_events":proxy_data,
            "badge_events":badge_data,
            "print_jobs":  printer_data,
        }
        with open(json_path, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"  JSON dump saved  → {BOLD}{CYAN}{json_path}{RESET}")

    section_header("📄  OUTPUT")
    print(f"  PDF report saved → {BOLD}{CYAN}{pdf_path}{RESET}\n")
    return pdf_path


def main():
    parser = argparse.ArgumentParser(
        prog="gumshoe",
        description="GumShoe Report — automated 24-hour insider threat triage for a target user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gumshoe jsmith --mock               # Run against simulated data
  gumshoe jdoe --output ./cases       # Save report to custom directory
  gumshoe jdoe --mock --json          # Also export raw JSON
  gumshoe jdoe --mock --no-color      # Plain text output (for logging)

Environment variables for live API mode:
  AD_API_BASE, AD_API_KEY
  PROXY_API_BASE, PROXY_API_KEY
  BADGE_API_BASE, BADGE_API_KEY
  PRINT_API_BASE, PRINT_API_KEY
        """,
    )
    parser.add_argument("username",    help="AD username to investigate (e.g. jsmith)")
    parser.add_argument("--mock",      action="store_true",
                        help="Use simulated data instead of live APIs")
    parser.add_argument("--output",    default="./reports",
                        help="Directory for output files (default: ./reports)")
    parser.add_argument("--json",      action="store_true",
                        help="Also export raw collected data as a JSON file")
    parser.add_argument("--no-color",  action="store_true",
                        help="Disable ANSI colour output (useful for log redirection)")

    args = parser.parse_args()

    if args.no_color:
        # Strip ANSI from all output by disabling colours at module level
        import gumshoe as _self
        for attr in ["RED","YELLOW","GREEN","CYAN","WHITE","DIM","MAGENTA","BOLD","RESET"]:
            globals()[attr] = ""

    try:
        run_triage(
            username   = args.username,
            mock       = args.mock,
            output_dir = args.output,
            dump_json  = args.json,
        )
    except KeyboardInterrupt:
        print(f"\n{YELLOW}  Triage interrupted by user.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
