CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.employee_raw (
    row_id BIGSERIAL PRIMARY KEY,
    client_employee_id TEXT,
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    preferred_name TEXT,
    job_code TEXT,
    job_title TEXT,
    job_start_date TEXT,
    organization_id TEXT,
    organization_name TEXT,
    department_id TEXT,
    department_name TEXT,
    dob TEXT,
    hire_date TEXT,
    recent_hire_date TEXT,
    anniversary_date TEXT,
    term_date TEXT,
    years_of_experience TEXT,
    work_email TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    country TEXT,
    manager_employee_id TEXT,
    manager_employee_name TEXT,
    fte_status TEXT,
    is_per_deim TEXT,
    cell_phone TEXT,
    work_phone TEXT,
    scheduled_weekly_hour TEXT,
    active_status TEXT,
    termination_reason TEXT,
    clinical_level TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw.timesheet_raw (
    row_id BIGSERIAL PRIMARY KEY,
    client_employee_id TEXT,
    department_id TEXT,
    department_name TEXT,
    home_department_id TEXT,
    home_department_name TEXT,
    pay_code TEXT,
    punch_in_comment TEXT,
    punch_out_comment TEXT,
    hours_worked TEXT,
    punch_apply_date TEXT,
    punch_in_datetime TEXT,
    punch_out_datetime TEXT,
    scheduled_start_datetime TEXT,
    scheduled_end_datetime TEXT,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE IF NOT EXISTS staging.employee_staging (
    client_employee_id TEXT PRIMARY KEY,
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    preferred_name TEXT,
    job_code TEXT,
    job_title TEXT,
    job_start_date DATE,
    organization_id TEXT,
    organization_name TEXT,
    department_id TEXT,
    department_name TEXT,
    dob DATE,
    hire_date DATE,
    recent_hire_date DATE,
    anniversary_date DATE,
    term_date DATE,
    years_of_experience NUMERIC,
    work_email TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    country TEXT,
    manager_employee_id TEXT,
    manager_employee_name TEXT,
    fte_status TEXT,
    is_per_deim BOOLEAN,
    cell_phone TEXT,
    work_phone TEXT,
    scheduled_weekly_hour NUMERIC,
    active_status BOOLEAN,
    termination_reason TEXT,
    clinical_level TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS staging.timesheet_staging (
    timesheet_id BIGSERIAL PRIMARY KEY,
    client_employee_id TEXT NOT NULL REFERENCES staging.employee_staging(client_employee_id),
    department_id TEXT,
    department_name TEXT,
    home_department_id TEXT,
    home_department_name TEXT,
    pay_code TEXT,
    punch_in_comment TEXT,
    punch_out_comment TEXT,
    hours_worked NUMERIC,
    punch_apply_date DATE,
    punch_in_datetime TIMESTAMP,
    punch_out_datetime TIMESTAMP,
    scheduled_start_datetime TIMESTAMP,
    scheduled_end_datetime TIMESTAMP,
    source_file TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT now(),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_timesheet_staging_employee_id
    ON staging.timesheet_staging (client_employee_id);

CREATE INDEX IF NOT EXISTS idx_timesheet_staging_punch_date
    ON staging.timesheet_staging (punch_apply_date);

CREATE INDEX IF NOT EXISTS idx_employee_staging_department
    ON staging.employee_staging (department_id);

CREATE INDEX IF NOT EXISTS idx_employee_staging_active_status
    ON staging.employee_staging (active_status);

CREATE SCHEMA IF NOT EXISTS curated;

CREATE TABLE IF NOT EXISTS curated.employee (
    client_employee_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    middle_name TEXT,
    last_name TEXT,
    preferred_name TEXT,
    full_name TEXT,
    job_code TEXT,
    job_title TEXT,
    job_start_date DATE,
    organization_id TEXT,
    organization_name TEXT,
    department_id TEXT,
    department_name TEXT,
    dob DATE,
    hire_date DATE NOT NULL,
    recent_hire_date DATE,
    anniversary_date DATE,
    term_date DATE,
    tenure_days INTEGER,
    years_of_experience NUMERIC,
    work_email TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    country TEXT,
    manager_employee_id TEXT,
    manager_employee_name TEXT,
    fte_status TEXT,
    is_per_deim BOOLEAN,
    cell_phone TEXT,
    work_phone TEXT,
    scheduled_weekly_hour NUMERIC,
    active_status BOOLEAN NOT NULL,
    termination_reason TEXT,
    clinical_level TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS curated.timesheet (
    timesheet_id BIGSERIAL PRIMARY KEY,
    client_employee_id TEXT NOT NULL REFERENCES curated.employee(client_employee_id),
    department_id TEXT,
    department_name TEXT,
    home_department_id TEXT,
    home_department_name TEXT,
    pay_code TEXT,
    hours_worked NUMERIC,
    punch_apply_date DATE NOT NULL,
    punch_in_datetime TIMESTAMP,
    punch_out_datetime TIMESTAMP,
    scheduled_start_datetime TIMESTAMP,
    scheduled_end_datetime TIMESTAMP,
    is_late_arrival BOOLEAN,
    is_early_departure BOOLEAN,
    is_overtime BOOLEAN,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (client_employee_id, punch_in_datetime, punch_out_datetime)
);

CREATE INDEX IF NOT EXISTS idx_curated_timesheet_employee_id
    ON curated.timesheet (client_employee_id);

CREATE INDEX IF NOT EXISTS idx_curated_timesheet_punch_date
    ON curated.timesheet (punch_apply_date);

CREATE INDEX IF NOT EXISTS idx_curated_employee_department
    ON curated.employee (department_id);

CREATE INDEX IF NOT EXISTS idx_curated_employee_active_status
    ON curated.employee (active_status);