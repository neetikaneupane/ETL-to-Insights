from sqlalchemy import (
    Column, String, Boolean, Integer, BigInteger, Numeric, Date, DateTime, Text, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class EmployeeRaw(Base):
    __tablename__ = "employee_raw"
    __table_args__ = {"schema": "raw"}

    row_id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_employee_id = Column(Text)
    first_name = Column(Text)
    middle_name = Column(Text)
    last_name = Column(Text)
    preferred_name = Column(Text)
    job_code = Column(Text)
    job_title = Column(Text)
    job_start_date = Column(Text)
    organization_id = Column(Text)
    organization_name = Column(Text)
    department_id = Column(Text)
    department_name = Column(Text)
    dob = Column(Text)
    hire_date = Column(Text)
    recent_hire_date = Column(Text)
    anniversary_date = Column(Text)
    term_date = Column(Text)
    years_of_experience = Column(Text)
    work_email = Column(Text)
    address = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip = Column(Text)
    country = Column(Text)
    manager_employee_id = Column(Text)
    manager_employee_name = Column(Text)
    fte_status = Column(Text)
    is_per_deim = Column(Text)
    cell_phone = Column(Text)
    work_phone = Column(Text)
    scheduled_weekly_hour = Column(Text)
    active_status = Column(Text)
    termination_reason = Column(Text)
    clinical_level = Column(Text)
    source_file = Column(Text, nullable=False)
    loaded_at = Column(DateTime, nullable=False, server_default=func.now())


class TimesheetRaw(Base):
    __tablename__ = "timesheet_raw"
    __table_args__ = {"schema": "raw"}

    row_id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_employee_id = Column(Text)
    department_id = Column(Text)
    department_name = Column(Text)
    home_department_id = Column(Text)
    home_department_name = Column(Text)
    pay_code = Column(Text)
    punch_in_comment = Column(Text)
    punch_out_comment = Column(Text)
    hours_worked = Column(Text)
    punch_apply_date = Column(Text)
    punch_in_datetime = Column(Text)
    punch_out_datetime = Column(Text)
    scheduled_start_datetime = Column(Text)
    scheduled_end_datetime = Column(Text)
    source_file = Column(Text, nullable=False)
    loaded_at = Column(DateTime, nullable=False, server_default=func.now())


class EmployeeStaging(Base):
    __tablename__ = "employee_staging"
    __table_args__ = {"schema": "staging"}

    client_employee_id = Column(Text, primary_key=True)
    first_name = Column(Text)
    middle_name = Column(Text)
    last_name = Column(Text)
    preferred_name = Column(Text)
    job_code = Column(Text)
    job_title = Column(Text)
    job_start_date = Column(Date)
    organization_id = Column(Text)
    organization_name = Column(Text)
    department_id = Column(Text)
    department_name = Column(Text)
    dob = Column(Date)
    hire_date = Column(Date)
    recent_hire_date = Column(Date)
    anniversary_date = Column(Date)
    term_date = Column(Date)
    years_of_experience = Column(Numeric)
    work_email = Column(Text)
    address = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip = Column(Text)
    country = Column(Text)
    manager_employee_id = Column(Text)
    manager_employee_name = Column(Text)
    fte_status = Column(Text)
    is_per_deim = Column(Boolean)
    cell_phone = Column(Text)
    work_phone = Column(Text)
    scheduled_weekly_hour = Column(Numeric)
    active_status = Column(Boolean)
    termination_reason = Column(Text)
    clinical_level = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now())


class TimesheetStaging(Base):
    __tablename__ = "timesheet_staging"
    __table_args__ = {"schema": "staging"}

    timesheet_id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_employee_id = Column(Text, ForeignKey("staging.employee_staging.client_employee_id"), nullable=False)
    department_id = Column(Text)
    department_name = Column(Text)
    home_department_id = Column(Text)
    home_department_name = Column(Text)
    pay_code = Column(Text)
    punch_in_comment = Column(Text)
    punch_out_comment = Column(Text)
    hours_worked = Column(Numeric)
    punch_apply_date = Column(Date)
    punch_in_datetime = Column(DateTime)
    punch_out_datetime = Column(DateTime)
    scheduled_start_datetime = Column(DateTime)
    scheduled_end_datetime = Column(DateTime)
    source_file = Column(Text, nullable=False)
    loaded_at = Column(DateTime, nullable=False, server_default=func.now())
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class EmployeeCurated(Base):
    __tablename__ = "employee"
    __table_args__ = {"schema": "curated"}

    client_employee_id = Column(Text, primary_key=True)
    first_name = Column(Text)
    middle_name = Column(Text)
    last_name = Column(Text)
    preferred_name = Column(Text)
    full_name = Column(Text)
    job_code = Column(Text)
    job_title = Column(Text)
    job_start_date = Column(Date)
    organization_id = Column(Text)
    organization_name = Column(Text)
    department_id = Column(Text)
    department_name = Column(Text)
    dob = Column(Date)
    hire_date = Column(Date)
    recent_hire_date = Column(Date)
    anniversary_date = Column(Date)
    term_date = Column(Date)
    tenure_days = Column(Integer)
    years_of_experience = Column(Numeric)
    work_email = Column(Text)
    address = Column(Text)
    city = Column(Text)
    state = Column(Text)
    zip = Column(Text)
    country = Column(Text)
    manager_employee_id = Column(Text)
    manager_employee_name = Column(Text)
    fte_status = Column(Text)
    is_per_deim = Column(Boolean)
    cell_phone = Column(Text)
    work_phone = Column(Text)
    scheduled_weekly_hour = Column(Numeric)
    active_status = Column(Boolean)
    termination_reason = Column(Text)
    clinical_level = Column(Text)
    is_placeholder = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    timesheets = relationship("TimesheetCurated", back_populates="employee")


class TimesheetCurated(Base):
    __tablename__ = "timesheet"
    __table_args__ = (
        UniqueConstraint("client_employee_id", "punch_in_datetime", "punch_out_datetime"),
        {"schema": "curated"},
    )

    timesheet_id = Column(BigInteger, primary_key=True, autoincrement=True)
    client_employee_id = Column(Text, ForeignKey("curated.employee.client_employee_id"), nullable=False)
    department_id = Column(Text)
    department_name = Column(Text)
    home_department_id = Column(Text)
    home_department_name = Column(Text)
    pay_code = Column(Text)
    hours_worked = Column(Numeric)
    punch_apply_date = Column(Date, nullable=False)
    punch_in_datetime = Column(DateTime)
    punch_out_datetime = Column(DateTime)
    scheduled_start_datetime = Column(DateTime)
    scheduled_end_datetime = Column(DateTime)
    is_late_arrival = Column(Boolean)
    is_early_departure = Column(Boolean)
    is_overtime = Column(Boolean)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    employee = relationship("EmployeeCurated", back_populates="timesheets")


class QualityCheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = {"schema": "quality"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_at = Column(DateTime, nullable=False, server_default=func.now())
    check_name = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    passed = Column(Boolean, nullable=False)
    metric_value = Column(Numeric)
    details = Column(Text)
