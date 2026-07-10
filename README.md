# ETL-to-Insights

End-to-end ETL pipeline with analytics generation, REST API, and interactive dashboard for employee workforce and timesheet data.

## Architecture

```
                    ┌──────────────┐
                    │   MinIO /    │
                    │  Local CSV   │
                    └──────┬───────┘
                           │ Extract
                    ┌──────▼───────┐
                    │  raw schema  │  (Bronze — raw data as loaded)
                    └──────┬───────┘
                           │ Transform
                    ┌──────▼───────┐
                    │staging schema│  (Silver — cleaned, typed, deduped)
                    └──────┬───────┘
                           │ Load / Curate
                    ┌──────▼───────┐
                    │curated schema│  (Gold — derived columns, business metrics)
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐ ┌───▼────┐ ┌────▼──────┐
       │  Analytics  │ │  API   │ │Dashboard  │
       │   SQL KPIs  │ │FastAPI │ │ Plotly.js │
       └────────────┘ └────────┘ └───────────┘
```

### Medallion Architecture (Bronze → Silver → Gold)

| Layer | Schema | Description |
|-------|--------|-------------|
| **Bronze** (raw) | `raw` | Raw CSV data loaded as-is, all columns stored as TEXT with source tracking |
| **Silver** (staging) | `staging` | Cleaned data with proper types (DATE, NUMERIC, BOOLEAN), deduplicated, validated |
| **Gold** (curated) | `curated` | Business-ready with derived metrics: `tenure_days`, `full_name`, `is_late_arrival`, `is_early_departure`, `is_overtime`, `is_placeholder` |
| **Quality** | `quality` | Automated check results for data integrity monitoring |

Staging and curated tables enforce **CHECK constraints** at the database level (`hours_worked >= 0`, `punch_out_datetime > punch_in_datetime`, `tenure_days >= 0`, `term_date >= hire_date`, etc.) for data integrity beyond application-level validation.

## ETL Pipeline

### Extract

Supports two modes, configured via `config/config.yaml` → `storage.source`:

- **local**: reads CSV files from `data/raw/employee/` and `data/raw/timesheet/`
- **minio**: reads from MinIO (S3-compatible) bucket using the configured prefix

### Transform

- Strips whitespace, parses dates/timestamps, coerces numerics and booleans
- Deduplicates employees keeping the most recently loaded record
- Filters junk/malformed employee IDs from timesheets (repeated digits, random strings, known junk IDs)
- Creates placeholder employee records for orphan timesheet references

### Load / Curate

- Computes derived columns: `full_name` (first + middle + last), `tenure_days` (hire_date to term_date or today)
- Computes attendance flags with configurable grace period (±5 min):
  - `is_late_arrival`: punch_in > scheduled_start + grace
  - `is_early_departure`: punch_out < scheduled_end - grace
  - `is_overtime`: actual_duration > scheduled_duration + grace
- Deduplicates timesheets by (employee_id, punch_in, punch_out)
- Uses upsert (ON CONFLICT DO UPDATE) for idempotent reruns

### Orchestration

Airflow DAG (`dags/etl_pipeline_dag.py`) with task dependencies:

```
extract → transform_employee → transform_timesheet → load_employee → load_timesheet → quality_check → generate_report
```

Each task has retry (3 attempts, 2 min apart). Can also run standalone:

```bash
python etl/extract/local_extractor.py
python etl/transform/employee_transform.py
python etl/transform/timesheet_transform.py
python etl/load/loader.py
python etl/quality_checks/validation.py
python -m etl.reporting.pipeline_report
```

### Quality Checks

Seven automated checks run at pipeline end. On failure, **diagnostic details** are captured (e.g., which employee IDs are duplicated, which rows have inverted dates) and stored in the `quality.check_results` table and JSON report.

| Check | Severity | Description |
|-------|----------|-------------|
| No duplicate employee IDs | critical | `client_employee_id` uniqueness in curated |
| No orphan timesheet refs | critical | Every timesheet has a valid employee |
| Hire before term | critical | No term_date before hire_date |
| Punch out after in | critical | No punch_out before or equal to punch_in |
| Null hire date (real) | warning | Real employees should have hire_date |
| Missing schedule % | warning | Percentage of timesheets without schedule data |
| Placeholder ratio % | warning | Percentage of placeholder employee records |

Results saved to `quality.check_results` table and JSON reports in `docs/quality_reports/`.

### Pipeline Reports

After quality checks, the DAG generates a pipeline report (`etl/reporting/pipeline_report.py`) in three formats:

| Format | Path | Contents |
|--------|------|----------|
| **Markdown** | `docs/pipeline_reports/pipeline_report_*.md` | Row counts per layer, quality check summary, duration |
| **HTML** | `docs/pipeline_reports/pipeline_report_*.html` | Same, rendered as a styled page |
| **JSON** | `docs/pipeline_reports/pipeline_report_*.json` | Machine-readable structured data |

Can also run standalone: `python -m etl.reporting.pipeline_report`

## Analytics (9 KPIs)

All queries in `analytics/queries/` — exposed via both SQL files and API endpoints.

| KPI | Endpoint | Window Functions | Joins |
|-----|----------|-----------------|-------|
| Active Headcount Over Time | `/analytics/headcount` | `generate_series` | LEFT JOIN employee |
| Turnover Trend | `/analytics/turnover` | `date_trunc` | — |
| Avg Tenure by Dept | `/analytics/tenure-by-department` | `AVG`, `ROUND` | GROUP BY department |
| Avg Working Hours | `/analytics/working-hours-summary` | `date_trunc('week')` | CTE + GROUP BY |
| Late Arrival Frequency | `/analytics/attendance-summary` | `FILTER(WHERE)` | — |
| Early Departure Count | `/analytics/attendance-summary` | `FILTER(WHERE)` | — |
| Total Overtime Count | `/analytics/attendance-summary` | `FILTER(WHERE)` | — |
| Rolling Avg Hours | `/analytics/rolling-hours-top` | `AVG OVER (ROWS BETWEEN)` | CTE + window |
| Early Attrition Rate | `/analytics/early-attrition` | `FILTER(WHERE)` | — |

## API (FastAPI)

### Authentication

All endpoints except `/health` and `/token` require JWT Bearer auth.

```bash
# Get token
curl -X POST http://localhost:8000/token \
  -d "grant_type=password&username=admin&password=changeme123"

# Use token
curl http://localhost:8000/employees \
  -H "Authorization: Bearer <token>"
```

### Employee CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/employees` | List all employees (filters: `department_name`, `active_status`) |
| GET | `/employees/{id}` | Get employee by ID |
| POST | `/employees` | Create new employee |
| PUT | `/employees/{id}` | Update employee fields |
| DELETE | `/employees/{id}` | Soft delete (sets `active_status=false`, `term_date=today`) |

### Timesheet (Read-only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/timesheets` | List timesheets (filters: `client_employee_id`, `start_date`, `end_date`) |
| GET | `/timesheets/employee/{id}` | Timesheets for a specific employee |

### Analytics

| Method | Endpoint | Returns |
|--------|----------|---------|
| GET | `/analytics/headcount` | Active headcount per month end |
| GET | `/analytics/turnover` | Terminations per month |
| GET | `/analytics/tenure-by-department` | Avg tenure years per department |
| GET | `/analytics/working-hours-summary` | Overall avg hours/day and hours/week |
| GET | `/analytics/attendance-summary` | Late arrival, early departure, overtime rates |
| GET | `/analytics/rolling-hours-top` | 7-day and 30-day rolling avg per employee |
| GET | `/analytics/early-attrition` | 90-day and 6-month early attrition counts |

## Dashboard

Interactive Plotly.js dashboard at `dashboard/index.html`:

1. Open `dashboard/index.html` in a browser
2. Log in with admin credentials (default: `admin` / `changeme123`)
3. Seven chart sections load from the live API

Charts: line (headcount), bar (turnover, attendance, rolling), horizontal bar (tenure), stat boxes (working hours, early attrition).

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 16
- Docker (optional, for containerized setup)

> **Sample data note:** The CSV source files in `data/raw/` are gitignored and not distributed with the repo. You need to provide your own pipe-delimited CSV files for employees and timesheets in `data/raw/employee/` and `data/raw/timesheet/` respectively. See [Data Format](#data-format) below for the expected schema.

### Data Format

Source CSV files are pipe-delimited (`|`) with UTF-8 encoding. Place files in:

| Entity | Directory |
|--------|-----------|
| Employees | `data/raw/employee/*.csv` |
| Timesheets | `data/raw/timesheet/*.csv` |

Files are read in alphabetical order. Null values can be represented as `""`, `[NULL]`, or `NULL`.

**Employee CSV** must include these columns:
`client_employee_id | first_name | last_name | department_id | department_name | hire_date | term_date` (any additional columns from the source system are accepted and passed through).

**Timesheet CSV** must include these columns:
`client_employee_id | hours_worked | punch_apply_date | punch_in_datetime | punch_out_datetime | scheduled_start_datetime | scheduled_end_datetime` (additional columns pass through).

See `etl/extract/local_extractor.py` for the full list of columns read from each file type.

### Quick Start (Local)

```bash
# 1. Clone and enter project
cd ETL-to-Insights

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp config/.env.example config/.env
# Edit config/.env with your PostgreSQL credentials

# 5. Create database
createdb etl_insights

# 6. Initialize schema
psql -d etl_insights -f database/schema/init_schema.sql

# 7. Run ETL pipeline
python etl/extract/local_extractor.py
python etl/transform/employee_transform.py
python etl/transform/timesheet_transform.py
python etl/load/loader.py
python etl/quality_checks/validation.py

# 8. Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000

# 9. Open dashboard
open dashboard/index.html
```

### Docker Compose

```bash
docker compose -f docker/docker-compose.yaml up -d
```

This starts PostgreSQL, MinIO, and Airflow (webserver on port 8081).

### Database Migrations

```bash
# Apply schema
python database/migrations/001_initial_schema.py

# Rollback
python database/migrations/001_initial_schema.py --down
```

### Running Tests

```bash
# Unit tests (no DB required)
pytest tests/ -v

# Integration tests (requires running API)
pytest tests/test_api.py -v

# Analytics query tests (requires populated DB)
pytest tests/test_analytics_queries.py -v
```

## Configuration

All configuration in `config/config.yaml` with environment variable expansion via `.env`:

| Key | Description |
|-----|-------------|
| `database.*` | PostgreSQL connection |
| `storage.source` | `local` or `minio` |
| `storage.local.*` | Local CSV file paths |
| `storage.minio.*` | MinIO endpoint, credentials, bucket |
| `file_format.delimiter` | CSV delimiter (`\|`) |
| `business_rules.grace_period_minutes` | Grace period for attendance flags |
| `business_rules.early_attrition_months` | Threshold for early attrition |
| `auth.*` | JWT secret, algorithm, expiry, admin credentials |

## Project Structure

```
├── analytics/queries/     # SQL KPI definitions
├── api/                   # FastAPI application
│   ├── auth/              # JWT auth logic
│   ├── routers/           # Employee, timesheet, analytics endpoints
│   └── schemas/           # Pydantic request/response models
├── config/                # YAML + .env configuration
├── dags/                  # Airflow DAG
├── dashboard/             # Plotly.js web dashboard
├── data/raw/              # Source CSV files
├── database/
│   ├── migrations/        # Schema migration scripts
│   ├── models/            # SQLAlchemy ORM models
│   └── schema/            # DDL init script
├── docker/                # Dockerfiles + docker-compose
├── docs/
│   ├── pipeline_reports/   # Pipeline run reports (HTML, MD, JSON)
│   └── quality_reports/    # Automated quality check reports
├── etl/
│   ├── extract/           # Local + MinIO extractors
│   ├── load/              # Curated load with derived columns
│   ├── quality_checks/    # Data quality validation
│   ├── reporting/         # Pipeline report generation (HTML, MD, JSON)
│   ├── transform/         # Data cleaning + staging
│   └── utils/             # DB connection, logging
├── logs/                  # Pipeline logs
└── tests/                 # pytest test suite
```

## Engineering Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | PostgreSQL | Strong SQL support, window functions, CTEs, Upsert (ON CONFLICT) |
| ETL | Python + Pandas | Rich data manipulation for CSV parsing, type coercion, dedup |
| Orchestration | Airflow | Industry standard, DAG-based dependencies, retry, scheduling |
| API | FastAPI | Async support, auto OpenAPI docs, Pydantic validation |
| Visualization | Plotly.js | Interactive browser charts, no server-side rendering |
| Auth | JWT + bcrypt | Stateless, no session store, standard OAuth2 flow |
| Architecture | Medallion (Bronze/Silver/Gold) | Clear data lineage, reprocessable layers, separation of concerns |
| Configuration | YAML + .env | Environment-specific overrides without touching code |
| Schema | SQL DDL (no ORM) | Explicit control over indexes, constraints, and data types |
