"""
PDF Report Generator — produces a formatted investigation report using ReportLab.
"""

from datetime import datetime

from reportlab.lib.pagesizes     import letter
from reportlab.lib.styles        import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units         import inch
from reportlab.lib               import colors
from reportlab.platypus          import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums         import TA_CENTER, TA_LEFT, TA_RIGHT

# ── colour palette ────────────────────────────────────────────────────────────
CLR_RED      = colors.HexColor("#C0392B")
CLR_ORANGE   = colors.HexColor("#E67E22")
CLR_YELLOW   = colors.HexColor("#F1C40F")
CLR_GREEN    = colors.HexColor("#27AE60")
CLR_BLUE     = colors.HexColor("#2980B9")
CLR_DARK     = colors.HexColor("#1A1A2E")
CLR_SLATE    = colors.HexColor("#2C3E50")
CLR_LIGHT_BG = colors.HexColor("#F2F4F7")
CLR_BORDER   = colors.HexColor("#BDC3C7")
CLR_WHITE    = colors.white

RISK_COLORS = {
    "CRITICAL": CLR_RED,
    "HIGH":     CLR_ORANGE,
    "MEDIUM":   CLR_YELLOW,
    "LOW":      CLR_GREEN,
}

RISK_HEX = {
    "CRITICAL": "#C0392B",
    "HIGH":     "#E67E22",
    "MEDIUM":   "#F1C40F",
    "LOW":      "#27AE60",
}


def _build_styles() -> dict:
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "CoverTitle", parent=base["Title"],
            fontSize=28, textColor=CLR_WHITE, leading=36,
            alignment=TA_CENTER, spaceAfter=8,
        ),
        "cover_sub": ParagraphStyle(
            "CoverSub", parent=base["Normal"],
            fontSize=13, textColor=colors.HexColor("#BDC3C7"),
            alignment=TA_CENTER, spaceAfter=4,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta", parent=base["Normal"],
            fontSize=10, textColor=colors.HexColor("#95A5A6"),
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading1"],
            fontSize=13, textColor=CLR_WHITE,
            backColor=CLR_SLATE, leading=18,
            leftIndent=-6, rightIndent=-6,
            spaceBefore=14, spaceAfter=8,
            borderPadding=(4, 8, 4, 8),
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"],
            fontSize=9, leading=13, spaceAfter=4,
        ),
        "indicator_high": ParagraphStyle(
            "IndHigh", parent=base["Normal"],
            fontSize=9, textColor=CLR_RED, leading=13,
        ),
        "indicator_medium": ParagraphStyle(
            "IndMed", parent=base["Normal"],
            fontSize=9, textColor=CLR_ORANGE, leading=13,
        ),
        "indicator_low": ParagraphStyle(
            "IndLow", parent=base["Normal"],
            fontSize=9, textColor=CLR_GREEN, leading=13,
        ),
        "table_header": ParagraphStyle(
            "TH", parent=base["Normal"],
            fontSize=8, textColor=CLR_WHITE, fontName="Helvetica-Bold",
        ),
        "table_cell": ParagraphStyle(
            "TC", parent=base["Normal"],
            fontSize=8, leading=11,
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"],
            fontSize=7, textColor=colors.HexColor("#95A5A6"),
            alignment=TA_CENTER,
        ),
        "risk_label": ParagraphStyle(
            "RiskLabel", parent=base["Normal"],
            fontSize=22, fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "score_label": ParagraphStyle(
            "ScoreLabel", parent=base["Normal"],
            fontSize=42, fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
    }
    return styles


def _risk_score_table(risk_report: dict, styles: dict):
    """Big visual risk score block."""
    level = risk_report["risk_level"]
    score = risk_report["risk_score"]
    clr   = RISK_COLORS.get(level, CLR_BLUE)
    hex_c = RISK_HEX.get(level, "#2980B9")

    score_p = Paragraph(f'<font color="{hex_c}"><b>{score}</b></font>/100', styles["score_label"])
    level_p = Paragraph(f'<font color="{hex_c}"><b>{level} RISK</b></font>', styles["risk_label"])

    tbl = Table([[score_p], [level_p]], colWidths=[6.5*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), CLR_LIGHT_BG),
        ("BOX",          (0,0), (-1,-1), 1.5, clr),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 12),
        ("BOTTOMPADDING",(0,0), (-1,-1), 12),
    ]))
    return tbl


def _data_table(headers: list, rows: list, styles: dict, col_widths=None):
    """Generic styled data table."""
    header_row = [Paragraph(h, styles["table_header"]) for h in headers]
    data = [header_row]
    for row in rows:
        data.append([Paragraph(str(c), styles["table_cell"]) for c in row])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND",    (0,0),  (-1,0),  CLR_SLATE),
        ("TEXTCOLOR",     (0,0),  (-1,0),  CLR_WHITE),
        ("FONTNAME",      (0,0),  (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),  (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),  (-1,-1), [CLR_WHITE, CLR_LIGHT_BG]),
        ("GRID",          (0,0),  (-1,-1), 0.4, CLR_BORDER),
        ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0),  (-1,-1), 4),
        ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
        ("LEFTPADDING",   (0,0),  (-1,-1), 6),
    ])
    tbl.setStyle(style)
    return tbl


def _header_footer(canvas, doc):
    """Draw page header and footer on every page."""
    canvas.saveState()
    w, h = letter

    # Header bar
    canvas.setFillColor(CLR_DARK)
    canvas.rect(0, h - 36, w, 36, fill=1, stroke=0)
    canvas.setFillColor(CLR_WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(0.5*inch, h - 23, "GUMSHOE REPORT")
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#BDC3C7"))
    canvas.drawRightString(w - 0.5*inch, h - 23, f"Page {doc.page}")

    # Footer
    canvas.setFillColor(colors.HexColor("#95A5A6"))
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w/2, 0.35*inch,
        "CONFIDENTIAL — FOR AUTHORIZED SECURITY PERSONNEL ONLY")
    canvas.restoreState()


def generate_pdf_report(
    username:     str,
    since:        datetime,
    ad_data:      list,
    proxy_data:   list,
    badge_data:   list,
    printer_data: list,
    risk_report:  dict,
    output_path:  str,
):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.6*inch, rightMargin=0.6*inch,
        topMargin=0.75*inch, bottomMargin=0.6*inch,
    )

    styles = _build_styles()
    story  = []
    W = 6.5 * inch   # usable width

    # ── Cover Page ────────────────────────────────────────────────────────────
    cover_data = [
        [Paragraph("GUMSHOE REPORT", styles["cover_title"])],
        [Paragraph("INVESTIGATION REPORT",  styles["cover_title"])],
        [Spacer(1, 0.2*inch)],
        [HRFlowable(width="80%", thickness=1, color=colors.HexColor("#5D6D7E"), spaceAfter=12)],
        [Paragraph(f"Subject: <b>{username.upper()}</b>", styles["cover_sub"])],
        [Paragraph(f"Investigation Period: {since.strftime('%Y-%m-%d %H:%M')} — {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["cover_meta"])],
        [Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["cover_meta"])],
        [Spacer(1, 0.15*inch)],
        [Paragraph("CLASSIFICATION: <b>CONFIDENTIAL</b>", styles["cover_meta"])],
    ]

    cover_tbl = Table(cover_data, colWidths=[W])
    cover_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), CLR_DARK),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 20),
        ("RIGHTPADDING",  (0,0), (-1,-1), 20),
    ]))
    story.append(Spacer(1, 1.2*inch))
    story.append(cover_tbl)
    story.append(PageBreak())

    # ── Risk Summary ──────────────────────────────────────────────────────────
    story.append(Paragraph("  EXECUTIVE SUMMARY", styles["section"]))
    story.append(Spacer(1, 6))
    story.append(_risk_score_table(risk_report, styles))
    story.append(Spacer(1, 12))

    if risk_report["indicators"]:
        ind_rows = []
        for ind in risk_report["indicators"]:
            sev = ind["severity"]
            sev_clr = "#C0392B" if sev == "HIGH" else ("#E67E22" if sev == "MEDIUM" else "#27AE60")
            ind_rows.append([
                Paragraph(f'<font color="{sev_clr}"><b>{sev}</b></font>', styles["table_cell"]),
                Paragraph(ind["category"],    styles["table_cell"]),
                Paragraph(ind["description"], styles["table_cell"]),
            ])
        ind_tbl = _data_table(
            ["SEVERITY", "CATEGORY", "INDICATOR DESCRIPTION"],
            [],
            styles,
            col_widths=[0.85*inch, 1.1*inch, 4.55*inch],
        )
        # rebuild with coloured rows
        header_row = [Paragraph(h, styles["table_header"]) for h in ["SEVERITY", "CATEGORY", "INDICATOR DESCRIPTION"]]
        ind_data = [header_row] + [
            [
                Paragraph(f'<font color="{"#C0392B" if i["severity"]=="HIGH" else "#E67E22" if i["severity"]=="MEDIUM" else "#27AE60"}"><b>{i["severity"]}</b></font>', styles["table_cell"]),
                Paragraph(i["category"],    styles["table_cell"]),
                Paragraph(i["description"], styles["table_cell"]),
            ]
            for i in risk_report["indicators"]
        ]
        ind_tbl2 = Table(ind_data, colWidths=[0.85*inch, 1.1*inch, 4.55*inch], repeatRows=1)
        ind_tbl2.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),  (-1,0),  CLR_SLATE),
            ("TEXTCOLOR",     (0,0),  (-1,0),  CLR_WHITE),
            ("FONTNAME",      (0,0),  (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0,0),  (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),  (-1,-1), [CLR_WHITE, CLR_LIGHT_BG]),
            ("GRID",          (0,0),  (-1,-1), 0.4, CLR_BORDER),
            ("VALIGN",        (0,0),  (-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),  (-1,-1), 5),
            ("BOTTOMPADDING", (0,0),  (-1,-1), 5),
            ("LEFTPADDING",   (0,0),  (-1,-1), 6),
        ]))
        story.append(ind_tbl2)
    else:
        story.append(Paragraph("No suspicious indicators detected.", styles["body"]))

    story.append(PageBreak())

    # ── AD Login Events ───────────────────────────────────────────────────────
    story.append(Paragraph("  ACTIVE DIRECTORY — LOGIN EVENTS", styles["section"]))
    story.append(Spacer(1, 4))
    if ad_data:
        rows = []
        for e in ad_data:
            res_clr = "#27AE60" if e["result"] == "SUCCESS" else "#C0392B"
            mfa_clr = "#27AE60" if e.get("mfa_used") else "#E67E22"
            rows.append([
                e["timestamp"],
                e["workstation"],
                e["source_ip"],
                f'<font color="{res_clr}"><b>{e["result"]}</b></font>',
                f'<font color="{mfa_clr}">{"YES" if e.get("mfa_used") else "NO"}</font>',
            ])
        formatted_rows = [
            [Paragraph(str(c), styles["table_cell"]) for c in row]
            for row in rows
        ]
        header_row = [Paragraph(h, styles["table_header"])
                      for h in ["TIMESTAMP", "WORKSTATION", "SOURCE IP", "RESULT", "MFA"]]
        login_tbl = Table([header_row] + formatted_rows,
                          colWidths=[1.45*inch, 1.5*inch, 1.25*inch, 0.95*inch, 0.6*inch],
                          repeatRows=1)
        login_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  CLR_SLATE),
            ("TEXTCOLOR",     (0,0), (-1,0),  CLR_WHITE),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [CLR_WHITE, CLR_LIGHT_BG]),
            ("GRID",          (0,0), (-1,-1), 0.4, CLR_BORDER),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 5),
            ("ALIGN",         (3,0), (4,-1),  "CENTER"),
        ]))
        story.append(login_tbl)
    else:
        story.append(Paragraph("No login events found.", styles["body"]))

    story.append(Spacer(1, 14))

    # ── Proxy Events ──────────────────────────────────────────────────────────
    story.append(Paragraph("  WEB PROXY — BROWSING HISTORY", styles["section"]))
    story.append(Spacer(1, 4))
    if proxy_data:
        HIGH_RISK_CATS = {"Cloud Storage", "File Sharing", "Anonymizer", "Data Exfil", "Malware"}
        proxy_rows = []
        for e in proxy_data:
            cat_clr = "#C0392B" if e["category"] in HIGH_RISK_CATS else (
                      "#E67E22" if e["category"] in ("Social Media",) else "#2C3E50")
            mb = e["bytes_transferred"] / 1_048_576
            bytes_str = f"{mb:,.1f} MB" if mb >= 1 else f"{e['bytes_transferred']:,} B"
            bytes_clr = "#C0392B" if e["bytes_transferred"] > 50_000_000 else "#2C3E50"
            proxy_rows.append([
                Paragraph(e["timestamp"], styles["table_cell"]),
                Paragraph(e["domain"], styles["table_cell"]),
                Paragraph(f'<font color="{cat_clr}"><b>{e["category"]}</b></font>', styles["table_cell"]),
                Paragraph(f'<font color="{bytes_clr}">{bytes_str}</font>', styles["table_cell"]),
            ])
        header_row = [Paragraph(h, styles["table_header"])
                      for h in ["TIMESTAMP", "DOMAIN", "CATEGORY", "DATA TRANSFERRED"]]
        proxy_tbl = Table([header_row] + proxy_rows,
                          colWidths=[1.45*inch, 2.0*inch, 1.6*inch, 1.45*inch],
                          repeatRows=1)
        proxy_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  CLR_SLATE),
            ("TEXTCOLOR",     (0,0), (-1,0),  CLR_WHITE),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [CLR_WHITE, CLR_LIGHT_BG]),
            ("GRID",          (0,0), (-1,-1), 0.4, CLR_BORDER),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ]))
        story.append(proxy_tbl)
    else:
        story.append(Paragraph("No proxy events found.", styles["body"]))

    story.append(PageBreak())

    # ── Badge Events ──────────────────────────────────────────────────────────
    story.append(Paragraph("  PHYSICAL ACCESS — BADGE SWIPES", styles["section"]))
    story.append(Spacer(1, 4))
    if badge_data:
        badge_rows = []
        for e in badge_data:
            dir_clr = "#2980B9" if e["direction"] == "ENTRY" else "#16A085"
            res_clr = "#27AE60" if e["result"] == "GRANTED" else "#C0392B"
            badge_rows.append([
                Paragraph(e["timestamp"], styles["table_cell"]),
                Paragraph(e["location"],  styles["table_cell"]),
                Paragraph(f'<font color="{dir_clr}"><b>{e["direction"]}</b></font>', styles["table_cell"]),
                Paragraph(f'<font color="{res_clr}"><b>{e["result"]}</b></font>', styles["table_cell"]),
            ])
        header_row = [Paragraph(h, styles["table_header"])
                      for h in ["TIMESTAMP", "LOCATION", "DIRECTION", "RESULT"]]
        badge_tbl = Table([header_row] + badge_rows,
                          colWidths=[1.45*inch, 3.0*inch, 1.0*inch, 1.05*inch],
                          repeatRows=1)
        badge_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  CLR_SLATE),
            ("TEXTCOLOR",     (0,0), (-1,0),  CLR_WHITE),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [CLR_WHITE, CLR_LIGHT_BG]),
            ("GRID",          (0,0), (-1,-1), 0.4, CLR_BORDER),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ]))
        story.append(badge_tbl)
    else:
        story.append(Paragraph("No badge events found.", styles["body"]))

    story.append(Spacer(1, 14))

    # ── Printing Events ───────────────────────────────────────────────────────
    story.append(Paragraph("  PRINTING ACTIVITY", styles["section"]))
    story.append(Spacer(1, 4))
    if printer_data:
        print_rows = []
        SENSITIVE_KW = ("confidential","classified","employee","ssn","database",
                        "export","source","ip_transfer","salary","customer")
        for e in printer_data:
            total_p = e["pages"] * e.get("copies", 1)
            doc_clr = "#C0392B" if any(kw in e["document_name"].lower() for kw in SENSITIVE_KW) else "#2C3E50"
            vol_clr = "#C0392B" if total_p > 50 else "#2C3E50"
            print_rows.append([
                Paragraph(e["timestamp"],   styles["table_cell"]),
                Paragraph(e["printer"],     styles["table_cell"]),
                Paragraph(f'<font color="{doc_clr}">{e["document_name"]}</font>', styles["table_cell"]),
                Paragraph(f'<font color="{vol_clr}">{e["pages"]}</font>', styles["table_cell"]),
                Paragraph(f'<font color="{vol_clr}">{e.get("copies",1)}</font>', styles["table_cell"]),
                Paragraph(f'<font color="{vol_clr}"><b>{total_p}</b></font>', styles["table_cell"]),
            ])
        header_row = [Paragraph(h, styles["table_header"])
                      for h in ["TIMESTAMP", "PRINTER", "DOCUMENT NAME", "PGS", "COPIES", "TOTAL"]]
        print_tbl = Table([header_row] + print_rows,
                          colWidths=[1.4*inch, 1.2*inch, 2.3*inch, 0.5*inch, 0.6*inch, 0.5*inch],
                          repeatRows=1)
        print_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  CLR_SLATE),
            ("TEXTCOLOR",     (0,0), (-1,0),  CLR_WHITE),
            ("FONTSIZE",      (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [CLR_WHITE, CLR_LIGHT_BG]),
            ("GRID",          (0,0), (-1,-1), 0.4, CLR_BORDER),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 5),
            ("ALIGN",         (3,0), (-1,-1), "CENTER"),
        ]))
        story.append(print_tbl)
    else:
        story.append(Paragraph("No print jobs found.", styles["body"]))

    story.append(Spacer(1, 20))

    # ── Analyst Notes ─────────────────────────────────────────────────────────
    story.append(Paragraph("  ANALYST NOTES", styles["section"]))
    story.append(Spacer(1, 4))
    notes_style = ParagraphStyle("Notes", parent=getSampleStyleSheet()["Normal"],
                                 fontSize=9, leading=14, textColor=colors.HexColor("#5D6D7E"),
                                 borderColor=CLR_BORDER, borderWidth=0.5,
                                 borderPadding=(8,10,8,10), backColor=CLR_LIGHT_BG)
    story.append(Paragraph(
        "[ Space reserved for investigator comments, chain-of-custody notes, and escalation decisions. ]",
        notes_style,
    ))
    for _ in range(6):
        story.append(HRFlowable(width="100%", thickness=0.5, color=CLR_BORDER, spaceAfter=18))

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
