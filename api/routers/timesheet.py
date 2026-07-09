from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import MetaData, Table, select
from sqlalchemy.engine import Connection

from api.dependencies import get_db
from api.auth.auth import get_current_user
from api.schemas.schemas import TimesheetResponse

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


def get_timesheet_table(conn: Connection):
    meta = MetaData(schema="curated")
    return Table("timesheet", meta, autoload_with=conn)


@router.get("", response_model=List[TimesheetResponse])
def list_timesheets(
    client_employee_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    table = get_timesheet_table(conn)
    query = select(table)

    if client_employee_id is not None:
        query = query.where(table.c.client_employee_id == client_employee_id)
    if start_date is not None:
        query = query.where(table.c.punch_apply_date >= start_date)
    if end_date is not None:
        query = query.where(table.c.punch_apply_date <= end_date)

    query = query.order_by(table.c.punch_apply_date.desc()).limit(limit).offset(offset)
    results = conn.execute(query).all()
    return [row._mapping for row in results]


@router.get("/employee/{employee_id}", response_model=List[TimesheetResponse])
def get_employee_timesheets(
    employee_id: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    table = get_timesheet_table(conn)
    query = select(table).where(table.c.client_employee_id == employee_id)

    if start_date is not None:
        query = query.where(table.c.punch_apply_date >= start_date)
    if end_date is not None:
        query = query.where(table.c.punch_apply_date <= end_date)

    query = query.order_by(table.c.punch_apply_date.desc()).limit(limit).offset(offset)
    results = conn.execute(query).all()

    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No timesheet entries found for employee {employee_id}",
        )

    return [row._mapping for row in results]