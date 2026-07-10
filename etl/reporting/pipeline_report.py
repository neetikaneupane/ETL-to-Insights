import os
import json
from decimal import Decimal
from datetime import datetime
from sqlalchemy import text
from etl.utils.db_connection import get_engine
from etl.utils.logger import get_logger

logger = get_logger(__name__)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(BASE_DIR, "docs", "pipeline_reports")


def get_row_counts(engine):
    queries = {
        "raw.employee_raw": "SELECT COUNT(*) FROM raw.employee_raw",
        "raw.timesheet_raw": "SELECT COUNT(*) FROM raw.timesheet_raw",
        "staging.employee_staging": "SELECT COUNT(*) FROM staging.employee_staging",
        "staging.timesheet_staging": "SELECT COUNT(*) FROM staging.timesheet_staging",
        "curated.employee": "SELECT COUNT(*) FROM curated.employee",
        "curated.timesheet": "SELECT COUNT(*) FROM curated.timesheet",
        "curated.employee (active)": "SELECT COUNT(*) FROM curated.employee WHERE active_status = true",
        "curated.employee (placeholder)": "SELECT COUNT(*) FROM curated.employee WHERE is_placeholder = true",
    }
    counts = {}
    with engine.connect() as conn:
        for label, query in queries.items():
            result = conn.execute(text(query)).scalar()
            counts[label] = result
    return counts


def get_quality_summary(engine):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT check_name, severity, passed, metric_value, details
                FROM quality.check_results
                ORDER BY run_at DESC
                LIMIT 7
            """)
        ).fetchall()
    return [
        {
            "check_name": r[0],
            "severity": r[1],
            "passed": r[2],
            "metric_value": r[3],
            "details": r[4],
        }
        for r in rows
    ]


def generate_markdown_report(run_ts, row_counts, quality_results, duration_secs):
    lines = []
    lines.append(f"# ETL Pipeline Report")
    lines.append(f"")
    lines.append(f"- **Run timestamp:** {run_ts}")
    lines.append(f"- **Duration:** {duration_secs:.1f}s")
    lines.append(f"")
    lines.append(f"## Row Counts")
    lines.append(f"")
    lines.append(f"| Layer | Table | Rows |")
    lines.append(f"|-------|-------|------|")
    for label, count in row_counts.items():
        lines.append(f"| {label.split('.')[0]} | {'.'.join(label.split('.')[1:])} | {count:,} |")
    lines.append(f"")
    lines.append(f"## Quality Checks")
    lines.append(f"")
    lines.append(f"| Check | Severity | Result | Value | Details |")
    lines.append(f"|-------|----------|--------|-------|---------|")
    for qr in quality_results:
        status = "✅ PASS" if qr["passed"] else "❌ FAIL"
        val = f"{qr['metric_value']}" if qr["metric_value"] is not None else "-"
        details = qr["details"] or "-"
        lines.append(f"| {qr['check_name']} | {qr['severity']} | {status} | {val} | {details} |")
    lines.append(f"")
    passed = sum(1 for qr in quality_results if qr["passed"])
    total = len(quality_results)
    lines.append(f"**{passed}/{total} checks passed**")
    lines.append(f"")
    return "\n".join(lines)


def generate_html_report(run_ts, row_counts, quality_results, duration_secs):
    rows_html = ""
    for label, count in row_counts.items():
        layer = label.split(".")[0]
        table = ".".join(label.split(".")[1:])
        rows_html += f"<tr><td>{layer}</td><td>{table}</td><td>{count:,}</td></tr>\n"

    checks_html = ""
    for qr in quality_results:
        status_icon = "&#9989;" if qr["passed"] else "&#10060;"
        val = f"{qr['metric_value']}" if qr["metric_value"] is not None else "-"
        details = qr["details"] or "-"
        checks_html += (
            f"<tr><td>{qr['check_name']}</td><td>{qr['severity']}</td>"
            f"<td>{status_icon}</td><td>{val}</td><td>{details}</td></tr>\n"
        )

    passed = sum(1 for qr in quality_results if qr["passed"])
    total = len(quality_results)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Pipeline Report - {run_ts}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 1000px; margin: 2em auto; padding: 0 1em; }}
h1 {{ color: #333; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f5f5f5; }}
tr:nth-child(even) {{ background: #fafafa; }}
.summary {{ font-size: 1.1em; margin: 1em 0; }}
</style></head>
<body>
<h1>ETL Pipeline Report</h1>
<p class="summary"><strong>Run:</strong> {run_ts} &mdash; <strong>Duration:</strong> {duration_secs:.1f}s</p>
<h2>Row Counts</h2>
<table><thead><tr><th>Layer</th><th>Table</th><th>Rows</th></tr></thead><tbody>
{rows_html}</tbody></table>
<h2>Quality Checks</h2>
<table><thead><tr><th>Check</th><th>Severity</th><th>Result</th><th>Value</th><th>Details</th></tr></thead><tbody>
{checks_html}</tbody></table>
<p><strong>{passed}/{total} checks passed</strong></p>
</body></html>"""


def run_pipeline_report():
    logger.info("Starting pipeline report generation")
    start = datetime.now()
    run_ts = start.strftime("%Y-%m-%d %H:%M:%S")
    engine = get_engine()

    row_counts = get_row_counts(engine)
    quality_results = get_quality_summary(engine)
    duration = (datetime.now() - start).total_seconds()

    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts_safe = start.strftime("%Y%m%d_%H%M%S")

    md_path = os.path.join(REPORTS_DIR, f"pipeline_report_{ts_safe}.md")
    with open(md_path, "w") as f:
        f.write(generate_markdown_report(run_ts, row_counts, quality_results, duration))
    logger.info(f"Markdown report saved to {md_path}")

    html_path = os.path.join(REPORTS_DIR, f"pipeline_report_{ts_safe}.html")
    with open(html_path, "w") as f:
        f.write(generate_html_report(run_ts, row_counts, quality_results, duration))
    logger.info(f"HTML report saved to {html_path}")

    summary = {
        "timestamp": run_ts,
        "duration_seconds": duration,
        "row_counts": row_counts,
        "quality_checks": quality_results,
    }
    json_path = os.path.join(REPORTS_DIR, f"pipeline_report_{ts_safe}.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, cls=DecimalEncoder)
    logger.info(f"JSON report saved to {json_path}")

    logger.info(f"Pipeline report finished ({duration:.1f}s)")
    return summary


if __name__ == "__main__":
    run_pipeline_report()
