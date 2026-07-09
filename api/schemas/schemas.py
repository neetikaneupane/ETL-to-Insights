from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class EmployeeBase(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None
    job_code: Optional[str] = None
    job_title: Optional[str] = None
    job_start_date: Optional[date] = None
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    dob: Optional[date] = None
    hire_date: Optional[date] = None
    recent_hire_date: Optional[date] = None
    anniversary_date: Optional[date] = None
    term_date: Optional[date] = None
    years_of_experience: Optional[float] = None
    work_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    manager_employee_id: Optional[str] = None
    manager_employee_name: Optional[str] = None
    fte_status: Optional[str] = None
    is_per_deim: Optional[bool] = None
    cell_phone: Optional[str] = None
    work_phone: Optional[str] = None
    scheduled_weekly_hour: Optional[float] = None
    active_status: Optional[bool] = True
    termination_reason: Optional[str] = None
    clinical_level: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    client_employee_id: str = Field(..., description="Unique employee identifier")


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_name: Optional[str] = None
    job_code: Optional[str] = None
    job_title: Optional[str] = None
    job_start_date: Optional[date] = None
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    dob: Optional[date] = None
    hire_date: Optional[date] = None
    recent_hire_date: Optional[date] = None
    anniversary_date: Optional[date] = None
    term_date: Optional[date] = None
    years_of_experience: Optional[float] = None
    work_email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None
    manager_employee_id: Optional[str] = None
    manager_employee_name: Optional[str] = None
    fte_status: Optional[str] = None
    is_per_deim: Optional[bool] = None
    cell_phone: Optional[str] = None
    work_phone: Optional[str] = None
    scheduled_weekly_hour: Optional[float] = None
    active_status: Optional[bool] = None
    termination_reason: Optional[str] = None
    clinical_level: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    client_employee_id: str
    full_name: Optional[str] = None
    tenure_days: Optional[int] = None
    is_placeholder: Optional[bool] = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimesheetResponse(BaseModel):
    timesheet_id: int
    client_employee_id: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    home_department_id: Optional[str] = None
    home_department_name: Optional[str] = None
    pay_code: Optional[str] = None
    hours_worked: Optional[float] = None
    punch_apply_date: Optional[date] = None
    punch_in_datetime: Optional[datetime] = None
    punch_out_datetime: Optional[datetime] = None
    scheduled_start_datetime: Optional[datetime] = None
    scheduled_end_datetime: Optional[datetime] = None
    source_file: Optional[str] = None

    class Config:
        from_attributes = True