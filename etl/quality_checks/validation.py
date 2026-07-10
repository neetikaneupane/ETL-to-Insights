import os
import json
from datetime import datetime
from sqlalchemy import text
from etl.utils.db_connection import get_engine, load_config
from etl.utils.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(BASE_DIR, "docs", "quality_reports")


class QualityCheckFailure(Exception):
    pass


def run_check(engine, name, severity, query, threshold_check, details_query=None):
    with engine.connect() as conn:
        result = conn.execute(text(query)).scalar()

    passed = threshold_check(result)

    details = None
    if not passed and details_query:
        with engine.connect() as conn:
            raw = conn.execute(text(details_query)).fetchall()
        details = "; ".join(str(r[0]) for r in raw[:5]) if raw else None
        if len(raw) > 5:
            details += f" (and {len(raw) - 5} more)"

    return {
        "check_name": name,
        "severity": severity,
        "passed": bool(passed),
        "metric_value": float(result) if result is not None else None,
        "details": details,
    }


def get_checks(engine):
    config = load_config()
    qc = config.get("quality_checks", {})
    zero_tol = qc.get("zero_tolerance_critical", 0)
    missing_pct = qc.get("missing_schedule_percentage_threshold", 10)
    placeholder_pct = qc.get("placeholder_ratio_percentage_threshold", 50)

    def max_allowed(threshold):
        return lambda v: v is not None and v <= threshold

    checks = []

    checks.append(run_check(
        engine, "curated_employee_no_duplicate_ids", "critical",
        "SELECT COUNT(*) - COUNT(DISTINCT client_employee_id) FROM curated.employee",
        max_allowed(zero_tol),
        details_query="""
            SELECT client_employee_id || ': ' || COUNT(*)::TEXT || ' duplicates'
            FROM curated.employee
            GROUP BY client_employee_id
            HAVING COUNT(*) > 1
            LIMIT 5
        """,
    ))

    checks.append(run_check(
        engine, "curated_timesheet_orphan_employee_refs", "critical",
        """
        SELECT COUNT(*) FROM curated.timesheet t
        LEFT JOIN curated.employee e ON t.client_employee_id = e.client_employee_id
        WHERE e.client_employee_id IS NULL
        """,
        max_allowed(zero_tol),
        details_query="""
            SELECT DISTINCT t.client_employee_id || ': ' || COUNT(*)::TEXT || ' orphan rows'
            FROM curated.timesheet t
            LEFT JOIN curated.employee e ON t.client_employee_id = e.client_employee_id
            WHERE e.client_employee_id IS NULL
            GROUP BY t.client_employee_id
            LIMIT 5
        """,
    ))

    checks.append(run_check(
        engine, "curated_employee_hire_before_term", "critical",
        """
        SELECT COUNT(*) FROM curated.employee
        WHERE term_date IS NOT NULL AND hire_date IS NOT NULL AND term_date < hire_date
        """,
        max_allowed(zero_tol),
        details_query="""
            SELECT client_employee_id || ': hired ' || hire_date || ' term ' || term_date
            FROM curated.employee
            WHERE term_date IS NOT NULL AND hire_date IS NOT NULL AND term_date < hire_date
            LIMIT 5
        """,
    ))

    checks.append(run_check(
        engine, "curated_timesheet_punch_out_after_in", "critical",
        """
        SELECT COUNT(*) FROM curated.timesheet
        WHERE punch_in_datetime IS NOT NULL AND punch_out_datetime IS NOT NULL
        AND punch_out_datetime <= punch_in_datetime
        """,
        max_allowed(zero_tol),
        details_query="""
            SELECT client_employee_id || ': in=' || punch_in_datetime || ' out=' || punch_out_datetime
            FROM curated.timesheet
            WHERE punch_in_datetime IS NOT NULL AND punch_out_datetime IS NOT NULL
            AND punch_out_datetime <= punch_in_datetime
            LIMIT 5
        """,
    ))

    checks.append(run_check(
        engine, "curated_employee_null_hire_date_real_employees", "warning",
        """
        SELECT COUNT(*) FROM curated.employee
        WHERE is_placeholder = false AND hire_date IS NULL
        """,
        max_allowed(zero_tol),
        details_query="""
            SELECT client_employee_id || ': ' || COALESCE(first_name, '?') || ' ' || COALESCE(last_name, '?')
            FROM curated.employee
            WHERE is_placeholder = false AND hire_date IS NULL
            LIMIT 5
        """,
    ))

    checks.append(run_check(
        engine, "curated_timesheet_missing_schedule_percentage", "warning",
        """
        SELECT ROUND(
            100.0 * COUNT(*) FILTER (WHERE is_late_arrival IS NULL) / NULLIF(COUNT(*), 0), 2
        ) FROM curated.timesheet
        """,
        max_allowed(missing_pct),
    ))

    checks.append(run_check(
        engine, "curated_employee_placeholder_ratio_percentage", "warning",
        """
        SELECT ROUND(
            100.0 * COUNT(*) FILTER (WHERE is_placeholder = true) / NULLIF(COUNT(*), 0), 2
        ) FROM curated.employee
        """,
        max_allowed(placeholder_pct),
    ))

    return checks


def save_results_to_db(engine, results):
    with engine.begin() as conn:
        for r in results:
            conn.execute(
                text(
                    """
                    INSERT INTO quality.check_results
                        (check_name, severity, passed, metric_value, details)
                    VALUES
                        (:check_name, :severity, :passed, :metric_value, :details)
                    """
                ),
                {
                    "check_name": r["check_name"],
                    "severity": r["severity"],
                    "passed": r["passed"],
                    "metric_value": r["metric_value"],
                    "details": r.get("details"),
                },
            )


def save_results_to_json(results):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(REPORTS_DIR, f"quality_report_{timestamp}.json")

    with open(file_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Quality report saved to {file_path}")
    return file_path


def run_quality_checks():
    logger.info("Starting quality checks")
    engine = get_engine()

    results = get_checks(engine)

    for r in results:
        status = "PASSED" if r["passed"] else "FAILED"
        logger.info(
            f"[{r['severity'].upper()}] {r['check_name']}: {status} "
            f"(value={r['metric_value']})"
        )

    save_results_to_db(engine, results)
    save_results_to_json(results)

    critical_failures = [r for r in results if r["severity"] == "critical" and not r["passed"]]

    if critical_failures:
        failed_names = ", ".join(r["check_name"] for r in critical_failures)
        logger.error(f"Critical quality checks failed: {failed_names}")
        raise QualityCheckFailure(f"Critical quality checks failed: {failed_names}")

    logger.info("Quality checks finished, no critical failures")
    return results


if __name__ == "__main__":
    run_quality_checks()