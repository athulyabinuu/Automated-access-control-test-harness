from datetime import datetime
import json
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


NAVY = "#17324D"
BLUE = "#2563EB"
GREEN = "#15803D"
RED = "#B91C1C"
AMBER = "#B45309"
LIGHT_BLUE = "#EFF6FF"
LIGHT_GREY = "#F1F5F9"
MID_GREY = "#64748B"
DARK = "#0F172A"
BORDER = "#CBD5E1"


def _counts(results):
    passed = sum(1 for result in results if result.passed)

    failed = sum(
        1
        for result in results
        if not result.passed
        and not result.skipped
        and not result.error
    )

    skipped = sum(
        1
        for result in results
        if result.skipped
    )

    errors = sum(
        1
        for result in results
        if result.error
    )

    return passed, failed, skipped, errors


def _status(result):
    if result.error:
        return "ERROR"
    if result.skipped:
        return "SKIP"
    if result.passed:
        return "PASS"
    return "FAIL"


def _category_name(category):
    names = {
        "authentication": "Authentication",
        "invalid-token": "JWT Validation",
        "authenticated-access": "Authorization",
        "horizontal": "Horizontal Authorization / IDOR",
        "ownership": "Horizontal Authorization / IDOR",
        "vertical": "Vertical Authorization",
        "privileged-access": "Privileged Access",
    }

    return names.get(category, str(category).replace("-", " ").title())


def _category_counts(results):
    order = [
        "Authentication",
        "Authorization",
        "Horizontal Authorization / IDOR",
        "Vertical Authorization",
        "JWT Validation",
        "Privileged Access",
    ]

    counts = {
        name: {"total": 0, "passed": 0, "failed": 0}
        for name in order
    }

    for result in results:
        category = _category_name(result.category)

        if category not in counts:
            counts[category] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
            }

        counts[category]["total"] += 1

        if result.passed:
            counts[category]["passed"] += 1
        elif not result.skipped and not result.error:
            counts[category]["failed"] += 1

    return [
        (name, counts[name])
        for name in order
        if counts[name]["total"]
    ]


def _overall(passed, failed, skipped, errors):
    if failed == 0 and errors == 0:
        return "PASS"
    return "FAIL"


def _generated_time():
    return datetime.now().strftime(
        "%d %B %Y, %H:%M:%S"
    )


def _capabilities(results):
    categories = {
        _category_name(result.category)
        for result in results
    }

    preferred = [
        "RBAC",
        "JWT",
        "Vertical Authorization",
        "Horizontal Authorization / IDOR",
        "JWT Validation",
    ]

    capabilities = []

    if any(
        result.category
        in {
            "vertical",
            "privileged-access",
            "ownership",
            "horizontal",
        }
        for result in results
    ):
        capabilities.append("RBAC")

    if any(
        result.category in {
            "authentication",
            "invalid-token",
        }
        for result in results
    ):
        capabilities.append("JWT")

    if "Vertical Authorization" in categories:
        capabilities.append("Vertical Authorization")

    if "Horizontal Authorization / IDOR" in categories:
        capabilities.append("Horizontal Authorization / IDOR")

    if "JWT Validation" in categories:
        capabilities.append("JWT Validation")

    return [
        item
        for item in preferred
        if item in capabilities
    ]


def _result_rows(results):
    rows = []

    for result in results:
        status = _status(result)

        expected = ", ".join(
            str(value)
            for value in result.expected_statuses
        )

        actual = (
            str(result.actual_status)
            if result.actual_status is not None
            else "-"
        )

        finding = result.finding or ""
        error = result.error or ""

        rows.append(
            {
                "id": str(result.test_id),
                "role": str(result.role),
                "category": _category_name(result.category),
                "method": str(result.method),
                "endpoint": str(result.path),
                "rule": finding or error or "Control evaluated",
                "expected": expected,
                "actual": actual,
                "status": status,
                "finding": finding,
                "error": error,
                "evidence": str(result.evidence or ""),
                "request_url": str(result.request_url or ""),
                "response_body": result.response_body,
            }
        )

    return rows


def generate_json_report(
    results,
    target,
    output_file,
):
    rows = _result_rows(results)

    passed, failed, skipped, errors = _counts(results)

    report = {
        "report_type": "Automated Access Control Security Test Report",
        "generated_at": _generated_time(),
        "target": {
            "name": str(target.name),
            "base_url": str(target.base_url),
        },
        "summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "total": len(results),
            "overall": _overall(
                passed,
                failed,
                skipped,
                errors,
            ),
        },
        "categories": _category_counts(results),
        "tests": rows,
    }

    output_file = Path(output_file)

    output_file.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    return output_file



def generate_html_report(
    results,
    target,
    output_file,
):
    output_file = Path(output_file)
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    passed, failed, skipped, errors = _counts(results)
    total = len(results)
    overall = _overall(
        passed,
        failed,
        skipped,
        errors,
    )

    generated = _generated_time()
    capabilities = _capabilities(results)
    category_counts = _category_counts(results)
    rows = _result_rows(results)

    capability_text = " • ".join(capabilities)

    category_rows = []

    for category, counts in category_counts:
        category_rows.append(
            f"""
            <tr>
                <td>{escape(category)}</td>
                <td>{counts["total"]}</td>
                <td class="pass">{counts["passed"]}</td>
                <td class="fail">
                    {counts["failed"]}
                </td>
            </tr>
            """
        )

    detail_rows = []

    for row in rows:
        status_class = row["status"].lower()

        detail_rows.append(
            f"""
            <tr>
                <td class="id">{escape(row["id"])}</td>
                <td>{escape(row["role"])}</td>
                <td>{escape(row["category"])}</td>
                <td>{escape(row["method"])}</td>
                <td class="endpoint">
                    {escape(row["endpoint"])}
                </td>
                <td>{escape(row["rule"])}</td>
                <td>{escape(row["expected"])}</td>
                <td>{escape(row["actual"])}</td>
                <td>
                    <span class="badge {status_class}">
                        {"✓ " if row["status"] == "PASS" else ""}
                        {row["status"]}
                    </span>
                </td>
            </tr>
            """
        )

    findings = [
        row
        for row in rows
        if row["finding"] or row["error"]
    ]

    if findings:
        finding_cards = []

        for row in findings:
            response_body = row["response_body"]

            if response_body is None:
                response_text = ""
            elif isinstance(response_body, str):
                response_text = response_body
            else:
                response_text = str(response_body)

            finding_cards.append(
                f"""
                <div class="finding">
                    <div class="finding-title">
                        <strong>{escape(row["id"])}</strong>
                        <span>{escape(row["status"])}</span>
                    </div>

                    <div class="finding-label">Finding</div>
                    <div class="finding-value">
                        {escape(row["finding"] or row["error"])}
                    </div>

                    <div class="finding-label">Evidence</div>
                    <div class="finding-value">
                        {escape(row["evidence"] or "No evidence recorded.")}
                    </div>

                    <div class="finding-label">Request</div>
                    <div class="finding-value">
                        {escape(row["request_url"] or "No request URL recorded.")}
                    </div>

                    <div class="finding-meta">
                        <span>
                            <b>Expected:</b>
                            {escape(row["expected"])}
                        </span>
                        <span>
                            <b>Actual:</b>
                            {escape(row["actual"])}
                        </span>
                    </div>

                    <div class="finding-label">Response Body</div>
                    <pre class="finding-response">{escape(response_text)}</pre>
                </div>
                """
            )

        findings_html = "".join(finding_cards)
    else:
        findings_html = """
        <div class="finding success">
            <strong>No security findings</strong>
            <span>
                No authentication, authorization, horizontal-access,
                vertical-privilege, or JWT validation failures were
                identified during this assessment.
            </span>
        </div>
        """

    overall_class = (
        "overall-pass"
        if overall == "PASS"
        else "overall-fail"
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Automated Access Control Security Test Report</title>

<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: #f8fafc;
    color: {DARK};
    font-family: Arial, Helvetica, sans-serif;
    font-size: 13px;
}}

.page {{
    max-width: 1450px;
    margin: 0 auto;
    padding: 42px;
}}

.header {{
    border-bottom: 4px solid {NAVY};
    padding-bottom: 22px;
    margin-bottom: 26px;
}}

.brand {{
    color: {BLUE};
    font-size: 12px;
    font-weight: bold;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}}

h1 {{
    color: {NAVY};
    font-size: 30px;
    margin: 8px 0 16px;
}}

.subtitle {{
    color: {MID_GREY};
    font-size: 14px;
}}

.meta {{
    margin-top: 20px;
    line-height: 1.8;
}}

.meta strong {{
    color: {NAVY};
}}

.capabilities {{
    background: {LIGHT_BLUE};
    border-left: 4px solid {BLUE};
    padding: 13px 16px;
    margin: 22px 0;
    color: {NAVY};
    font-weight: bold;
}}

h2 {{
    color: {NAVY};
    font-size: 18px;
    border-bottom: 2px solid {BORDER};
    padding-bottom: 8px;
    margin-top: 32px;
}}

.summary {{
    display: grid;
    grid-template-columns:
        repeat(5, minmax(130px, 1fr));
    gap: 12px;
}}

.card {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 18px;
}}

.card-label {{
    color: {MID_GREY};
    font-size: 11px;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: .7px;
}}

.card-value {{
    color: {NAVY};
    font-size: 28px;
    font-weight: bold;
    margin-top: 7px;
}}

.card.pass .card-value {{
    color: {GREEN};
}}

.card.fail .card-value {{
    color: {RED};
}}

.overall {{
    margin: 22px 0;
    padding: 22px;
    border-radius: 8px;
    text-align: center;
    font-size: 22px;
    font-weight: bold;
}}

.overall-pass {{
    color: #166534;
    background: #f0fdf4;
    border: 1px solid #86efac;
}}

.overall-fail {{
    color: #991b1b;
    background: #fef2f2;
    border: 1px solid #fca5a5;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    background: white;
    margin-top: 12px;
}}

th {{
    background: {NAVY};
    color: white;
    padding: 10px;
    text-align: left;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: .4px;
}}

td {{
    border: 1px solid {BORDER};
    padding: 9px;
    vertical-align: top;
    line-height: 1.4;
}}

tbody tr:nth-child(even) {{
    background: #f8fafc;
}}

.id {{
    font-weight: bold;
    color: {NAVY};
    white-space: nowrap;
}}

.endpoint {{
    font-family: "Courier New", monospace;
    font-size: 12px;
}}

.pass {{
    color: {GREEN};
    font-weight: bold;
}}

.fail {{
    color: {RED};
    font-weight: bold;
}}

.badge {{
    display: inline-block;
    border-radius: 999px;
    padding: 4px 9px;
    font-size: 10px;
    font-weight: bold;
}}

.badge.pass {{
    color: #166534;
    background: #dcfce7;
}}

.badge.fail,
.badge.error {{
    color: #991b1b;
    background: #fee2e2;
}}

.badge.skip {{
    color: #92400e;
    background: #fef3c7;
}}

.finding {{
    padding: 14px;
    margin-top: 10px;
    background: #fff7ed;
    border-left: 4px solid {AMBER};
    border-radius: 4px;
}}

.finding.success {{
    background: #f0fdf4;
    border-left-color: {GREEN};
}}

.finding-title {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}}

.finding-label {{
    margin-top: 10px;
    margin-bottom: 3px;
    font-size: 11px;
    font-weight: 700;
    color: {MID_GREY};
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}

.finding-value {{
    line-height: 1.5;
    word-break: break-word;
}}

.finding-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid {BORDER};
    font-size: 12px;
}}

.finding-response {{
    margin: 5px 0 0;
    padding: 10px;
    background: #f8fafc;
    border: 1px solid {BORDER};
    border-radius: 4px;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: monospace;
    font-size: 11px;
    line-height: 1.45;
    overflow-x: auto;
}}

.meta {{
    margin-top: 24px;
    padding: 18px 22px;
    border: 1px solid {BORDER};
    border-radius: 10px;
    background: #f8fafc;
}}

.meta-row {{
    display: flex;
    align-items: flex-start;
    padding: 8px 0;
    border-bottom: 1px solid #e5e7eb;
}}

.meta-row:last-child {{
    border-bottom: none;
}}

.meta-label {{
    width: 150px;
    flex-shrink: 0;
    font-weight: 700;
    color: {DARK};
}}

.meta-value {{
    color: {MID_GREY};
    word-break: break-word;
}}

.footer {{
    margin-top: 40px;
    padding-top: 14px;
    border-top: 1px solid {BORDER};
    color: {MID_GREY};
    font-size: 11px;
    display: flex;
    justify-content: space-between;
}}

@media (max-width: 900px) {{
    .page {{
        padding: 20px;
    }}

    .summary {{
        grid-template-columns: repeat(2, 1fr);
    }}

    table {{
        font-size: 11px;
    }}
}}
</style>
</head>

<body>
<div class="page">

<div class="header">
    <div class="brand">
        AUTOMATED ACCESS CONTROL TEST HARNESS
    </div>

    <h1>
        Security Assessment Report
    </h1>

    <div class="subtitle">
        Automated Authentication &amp; Authorization Security Assessment
    </div>

    <div class="meta">
        <div class="meta-row">
            <span class="meta-label">Target</span>
            <span class="meta-value">{escape(target.name)}</span>
        </div>

        <div class="meta-row">
            <span class="meta-label">Target URL</span>
            <span class="meta-value">{escape(target.base_url)}</span>
        </div>

        <div class="meta-row">
            <span class="meta-label">Assessment Type</span>
            <span class="meta-value">Automated Access Control Security Testing</span>
        </div>

        <div class="meta-row">
            <span class="meta-label">Generated</span>
            <span class="meta-value">{escape(generated)}</span>
        </div>
    </div>
</div>

<div class="capabilities">
    {escape(capability_text)}
</div>

<h2>1. Executive Security Summary</h2>

<div class="summary">

<div class="card">
    <div class="card-label">Total Tests</div>
    <div class="card-value">{total}</div>
</div>

<div class="card pass">
    <div class="card-label">Passed</div>
    <div class="card-value">{passed}</div>
</div>

<div class="card fail">
    <div class="card-label">Failed</div>
    <div class="card-value">{failed}</div>
</div>

<div class="card">
    <div class="card-label">Skipped</div>
    <div class="card-value">{skipped}</div>
</div>

<div class="card">
    <div class="card-label">Errors</div>
    <div class="card-value">{errors}</div>
</div>

</div>

<div class="overall {overall_class}">
    {"✓ OVERALL SECURITY RESULT: PASS"
     if overall == "PASS"
     else "✗ OVERALL SECURITY RESULT: FAIL"}
</div>

<h2>2. Security Test Coverage</h2>

<table>
<thead>
<tr>
    <th>Security Category</th>
    <th>Total</th>
    <th>Passed</th>
    <th>Failed</th>
</tr>
</thead>

<tbody>
{''.join(category_rows)}
</tbody>
</table>

<h2>3. Assessment Scope</h2>

<p>
The assessment evaluated authentication enforcement, role-based
authorization, horizontal authorization boundaries, vertical
privilege separation, JWT validation, and protected API resource
access using the configured security policy and resource ownership
rules.
</p>

<h2>4. Detailed Security Test Results</h2>

<table>
<thead>
<tr>
    <th>ID</th>
    <th>Role</th>
    <th>Category</th>
    <th>Method</th>
    <th>Endpoint</th>
    <th>Rule</th>
    <th>Expected</th>
    <th>Actual</th>
    <th>Result</th>
</tr>
</thead>

<tbody>
{''.join(detail_rows)}
</tbody>
</table>

<h2>5. Security Findings</h2>

{findings_html}

<h2>6. Assessment Conclusion</h2>

<p>
A total of <strong>{total}</strong> automated security tests were
executed. <strong>{passed}</strong> passed,
<strong>{failed}</strong> failed,
<strong>{skipped}</strong> were skipped, and
<strong>{errors}</strong> produced errors.
</p>

<div class="overall {overall_class}">
    {"✓ OVERALL SECURITY RESULT: PASS"
     if overall == "PASS"
     else "✗ OVERALL SECURITY RESULT: FAIL"}
</div>

<div class="footer">
    <span>Automated Access Control Test Harness</span>
    <span>{escape(target.name)}</span>
</div>

</div>
</body>
</html>
"""

    output_file.write_text(
        html,
        encoding="utf-8",
    )

    return output_file


def generate_pdf_report(
    results,
    target,
    output_file,
):
    output_file = Path(output_file)
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    passed, failed, skipped, errors = _counts(results)
    total = len(results)
    overall = _overall(
        passed,
        failed,
        skipped,
        errors,
    )

    generated = _generated_time()
    category_counts = _category_counts(results)
    rows = _result_rows(results)
    capabilities = _capabilities(results)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        alignment=1,
        textColor=colors.HexColor("#123B5D"),
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor("#4B6475"),
        spaceAfter=18,
    )

    tool_name_style = ParagraphStyle(
        "ToolName",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        alignment=1,
        textColor=colors.HexColor("#FFFFFF"),
        spaceAfter=0,
    )

    report_title_style = ParagraphStyle(
        "ReportTitleProfessional",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        alignment=1,
        textColor=colors.HexColor("#123B5D"),
        spaceAfter=6,
    )

    report_subtitle_style = ParagraphStyle(
        "ReportSubtitleProfessional",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        alignment=1,
        textColor=colors.HexColor("#4B6475"),
        spaceAfter=14,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor(NAVY),
        spaceBefore=10,
        spaceAfter=6,
    )

    capability_style = ParagraphStyle(
        "CapabilityStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        alignment=1,
        textColor=colors.HexColor(MID_GREY),
        spaceAfter=8,
    )

    small_style = ParagraphStyle(
        "SmallStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=9.5,
        textColor=colors.HexColor(DARK),
        spaceAfter=2,
    )

    meta_data = [
        [
            Paragraph("<b>Target</b>", styles["Normal"]),
            Paragraph(
                escape(target.name),
                styles["Normal"],
            ),
        ],
        [
            Paragraph("<b>URL</b>", styles["Normal"]),
            Paragraph(
                escape(target.base_url),
                styles["Normal"],
            ),
        ],
        [
            Paragraph("<b>Assessment Type</b>", styles["Normal"]),
            Paragraph(
                "Automated Access Control Security Testing",
                styles["Normal"],
            ),
        ],
        [
            Paragraph("<b>Generated</b>", styles["Normal"]),
            Paragraph(
                escape(generated),
                styles["Normal"],
            ),
        ],
    ]

    meta_table = Table(
        meta_data,
        colWidths=[35 * mm, 145 * mm],
    )

    meta_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(LIGHT_GREY),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.HexColor(BORDER),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor(BORDER),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story = []

    header_table = Table(
        [
            [
                Paragraph(
                    "AUTOMATED ACCESS CONTROL TEST HARNESS",
                    tool_name_style,
                )
            ]
        ],
        colWidths=[180 * mm],
    )

    header_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#123B5D"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor("#123B5D"),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            "Security Assessment Report",
            report_title_style,
        )
    )

    story.append(
        Paragraph(
            "Automated Authentication &amp; Authorization Security Assessment",
            report_subtitle_style,
        )
    )

    story.append(meta_table)
    story.append(Spacer(1, 7))

    story.append(
        Paragraph(
            " • ".join(capabilities),
            capability_style,
        )
    )

    story.append(
        Paragraph(
            "1. EXECUTIVE SECURITY SUMMARY",
            heading_style,
        )
    )

    summary_data = [
        [
            Paragraph("<b>TOTAL</b>", styles["Normal"]),
            Paragraph("<b>PASSED</b>", styles["Normal"]),
            Paragraph("<b>FAILED</b>", styles["Normal"]),
            Paragraph("<b>SKIPPED</b>", styles["Normal"]),
            Paragraph("<b>ERRORS</b>", styles["Normal"]),
        ],
        [
            str(total),
            str(passed),
            str(failed),
            str(skipped),
            str(errors),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[36 * mm] * 5,
    )

    summary_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(NAVY),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, 1),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 1),
                    (-1, 1),
                    17,
                ),
                (
                    "TEXTCOLOR",
                    (1, 1),
                    (1, 1),
                    colors.HexColor(GREEN),
                ),
                (
                    "TEXTCOLOR",
                    (2, 1),
                    (2, 2),
                    colors.HexColor(RED),
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, 1),
                    colors.HexColor("#F8FAFC"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor(BORDER),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(BORDER),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(summary_table)
    story.append(Spacer(1, 7))

    overall_color = (
        GREEN
        if overall == "PASS"
        else RED
    )

    overall_table = Table(
        [
            [
                Paragraph(
                    (
                        "✓ OVERALL SECURITY RESULT: PASS"
                        if overall == "PASS"
                        else
                        "✗ OVERALL SECURITY RESULT: FAIL"
                    ),
                    ParagraphStyle(
                        "Overall",
                        parent=styles["Normal"],
                        fontName="Helvetica-Bold",
                        fontSize=13,
                        alignment=TA_CENTER,
                        textColor=colors.HexColor(
                            overall_color
                        ),
                    ),
                )
            ]
        ],
        colWidths=[180 * mm],
    )

    overall_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#F0FDF4"
                        if overall == "PASS"
                        else "#FEF2F2"
                    ),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor(overall_color),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ]
        )
    )

    story.append(overall_table)

    story.append(
        Paragraph(
            "2. SECURITY TEST COVERAGE",
            heading_style,
        )
    )

    category_data = [
        [
            Paragraph("<b>Security Category</b>", styles["Normal"]),
            Paragraph("<b>Total</b>", styles["Normal"]),
            Paragraph("<b>Passed</b>", styles["Normal"]),
            Paragraph("<b>Failed</b>", styles["Normal"]),
        ]
    ]

    for category, counts in category_counts:
        category_data.append(
            [
                Paragraph(
                    escape(category),
                    small_style,
                ),
                str(counts["total"]),
                str(counts["passed"]),
                str(counts["failed"]),
            ]
        )

    category_table = Table(
        category_data,
        colWidths=[105 * mm, 25 * mm, 25 * mm, 25 * mm],
        repeatRows=1,
    )

    category_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(NAVY),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.HexColor(BORDER),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
                (
                    "TEXTCOLOR",
                    (2, 1),
                    (2, -1),
                    colors.HexColor(GREEN),
                ),
                (
                    "TEXTCOLOR",
                    (3, 1),
                    (3, -1),
                    colors.HexColor(RED),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(category_table)

    story.append(
        Paragraph(
            "3. ASSESSMENT SCOPE",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            "The assessment evaluated authentication enforcement, "
            "role-based authorization, horizontal authorization "
            "boundaries, vertical privilege separation, JWT "
            "validation, and protected API resource access using "
            "the configured security policy and resource ownership "
            "rules.",
            styles["Normal"],
        )
    )

    story.append(
        Paragraph(
            "4. DETAILED SECURITY TEST RESULTS",
            heading_style,
        )
    )

    detail_data = [
        [
            Paragraph("<b>ID</b>", small_style),
            Paragraph("<b>ROLE</b>", small_style),
            Paragraph("<b>CATEGORY</b>", small_style),
            Paragraph("<b>METHOD</b>", small_style),
            Paragraph("<b>ENDPOINT</b>", small_style),
            Paragraph("<b>RULE</b>", small_style),
            Paragraph("<b>EXP.</b>", small_style),
            Paragraph("<b>ACT.</b>", small_style),
            Paragraph("<b>RESULT</b>", small_style),
        ]
    ]

    for row in rows:
        status = row["status"]

        result_text = (
            "✓ PASS"
            if status == "PASS"
            else status
        )

        detail_data.append(
            [
                Paragraph(
                    escape(row["id"]),
                    small_style,
                ),
                Paragraph(
                    escape(row["role"]),
                    small_style,
                ),
                Paragraph(
                    escape(row["category"]),
                    small_style,
                ),
                Paragraph(
                    escape(row["method"]),
                    small_style,
                ),
                Paragraph(
                    escape(row["endpoint"]),
                    small_style,
                ),
                Paragraph(
                    escape(row["rule"]),
                    small_style,
                ),
                Paragraph(
                    escape(row["expected"]),
                    small_style,
                ),
                Paragraph(
                    escape(row["actual"]),
                    small_style,
                ),
                Paragraph(
                    result_text,
                    ParagraphStyle(
                        "Result",
                        parent=small_style,
                        fontName="Helvetica-Bold",
                        textColor=colors.HexColor(
                            GREEN
                            if status == "PASS"
                            else RED
                        ),
                    ),
                ),
            ]
        )

    detail_table = Table(
        detail_data,
        colWidths=[
            14 * mm,   # ID
            20 * mm,   # Role
            43 * mm,   # Category
            16 * mm,   # Method
            39 * mm,   # Endpoint
            25 * mm,   # Rule
            14 * mm,   # Expected
            14 * mm,   # Actual
            22 * mm,   # Result
        ],
        repeatRows=1,
    )

    detail_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(NAVY),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor(BORDER),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(detail_table)

    story.append(
        Paragraph(
            "5. SECURITY FINDINGS",
            heading_style,
        )
    )

    finding_rows = [
        row
        for row in rows
        if row["finding"] or row["error"]
    ]

    if finding_rows:
        for row in finding_rows:
            response_body = row["response_body"]

            if response_body is None:
                response_text = "No response body recorded."
            elif isinstance(response_body, str):
                response_text = response_body
            else:
                response_text = str(response_body)

            finding_text = (
                row["finding"]
                or row["error"]
                or "No finding description recorded."
            )

            finding_data = [
                [
                    Paragraph(
                        f"<b>{escape(row['id'])}</b>",
                        styles["Normal"],
                    ),
                    Paragraph(
                        escape(row["status"]),
                        styles["Normal"],
                    ),
                ],
                [
                    Paragraph("<b>Finding</b>", small_style),
                    Paragraph(
                        escape(finding_text),
                        styles["Normal"],
                    ),
                ],
                [
                    Paragraph("<b>Evidence</b>", small_style),
                    Paragraph(
                        escape(
                            row["evidence"]
                            or "No evidence recorded."
                        ),
                        styles["Normal"],
                    ),
                ],
                [
                    Paragraph("<b>Request</b>", small_style),
                    Paragraph(
                        escape(
                            row["request_url"]
                            or "No request URL recorded."
                        ),
                        styles["Normal"],
                    ),
                ],
                [
                    Paragraph("<b>Expected</b>", small_style),
                    Paragraph(
                        escape(row["expected"]),
                        styles["Normal"],
                    ),
                ],
                [
                    Paragraph("<b>Actual</b>", small_style),
                    Paragraph(
                        escape(row["actual"]),
                        styles["Normal"],
                    ),
                ],
                [
                    Paragraph("<b>Response Body</b>", small_style),
                    Paragraph(
                        escape(response_text),
                        styles["Normal"],
                    ),
                ],
            ]

            finding_table = Table(
                finding_data,
                colWidths=[32 * mm, 148 * mm],
                repeatRows=1,
            )

            finding_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor(NAVY),
                        ),
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            colors.white,
                        ),
                        (
                            "BACKGROUND",
                            (0, 1),
                            (0, -1),
                            colors.HexColor(LIGHT_GREY),
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.4,
                            colors.HexColor(BORDER),
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            5,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            5,
                        ),
                    ]
                )
            )

            story.append(finding_table)
            story.append(Spacer(1, 5 * mm))

    else:
        no_findings = Table(
            [
                [
                    Paragraph(
                        "<b>No security findings.</b> "
                        "No evaluated authentication or "
                        "authorization control produced a "
                        "failure during this assessment.",
                        styles["Normal"],
                    )
                ]
            ],
            colWidths=[180 * mm],
        )

        no_findings.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#F0FDF4"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        colors.HexColor(GREEN),
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                ]
            )
        )

        story.append(no_findings)

    story.append(
        Paragraph(
            "6. ASSESSMENT CONCLUSION",
            heading_style,
        )
    )

    story.append(
        Paragraph(
            f"A total of <b>{total}</b> automated security "
            f"tests were executed. <b>{passed}</b> passed, "
            f"<b>{failed}</b> failed, <b>{skipped}</b> were "
            f"skipped, and <b>{errors}</b> produced errors.",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 8))

    final_table = Table(
        [
            [
                Paragraph(
                    (
                        "✓ OVERALL SECURITY RESULT: PASS"
                        if overall == "PASS"
                        else
                        "✗ OVERALL SECURITY RESULT: FAIL"
                    ),
                    ParagraphStyle(
                        "FinalResult",
                        parent=styles["Normal"],
                        fontName="Helvetica-Bold",
                        fontSize=13,
                        alignment=TA_CENTER,
                        textColor=colors.HexColor(
                            overall_color
                        ),
                    ),
                )
            ]
        ],
        colWidths=[180 * mm],
    )

    final_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#F0FDF4"
                        if overall == "PASS"
                        else "#FEF2F2"
                    ),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor(overall_color),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
            ]
        )
    )

    story.append(final_table)

    document = SimpleDocTemplate(
        str(output_file),
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title="Automated Access Control Security Test Report",
        author="Automated Access Control Test Harness",
    )

    def footer(canvas, doc):
        canvas.saveState()

        width, height = landscape(A4)

        canvas.setStrokeColor(
            colors.HexColor(BORDER)
        )
        canvas.line(
            15 * mm,
            12 * mm,
            width - 15 * mm,
            12 * mm,
        )

        canvas.setFont(
            "Helvetica",
            7,
        )
        canvas.setFillColor(
            colors.HexColor(MID_GREY)
        )

        canvas.drawString(
            15 * mm,
            7 * mm,
            "Automated Access Control Test Harness",
        )

        canvas.drawRightString(
            width - 15 * mm,
            7 * mm,
            f"{target.name} • Page {doc.page}",
        )

        canvas.restoreState()

    document.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer,
    )

    return output_file
