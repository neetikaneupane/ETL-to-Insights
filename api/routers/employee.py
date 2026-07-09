from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import MetaData, Table, select, insert, update
from sqlalchemy.engine import Connection

from api.dependencies import get_db
from api.auth.auth import get_current_user
from api.schemas.schemas import EmployeeCreate, EmployeeUpdate, EmployeeResponse

router = APIRouter(prefix="/employees", tags=["employees"])


def get_employee_table(conn: Connection):
    meta = MetaData(schema="staging")
    return Table("employee_staging", meta, autoload_with=conn)


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee: EmployeeCreate,
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    table = get_employee_table(conn)

    existing = conn.execute(
        select(table).where(table.c.client_employee_id == employee.client_employee_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee with id {employee.client_employee_id} already exists",
        )

    data = employee.model_dump()
    data["created_at"] = datetime.utcnow()
    data["updated_at"] = datetime.utcnow()

    conn.execute(insert(table).values(**data))
    conn.commit()

    result = conn.execute(
        select(table).where(table.c.client_employee_id == employee.client_employee_id)
    ).first()
    return result._mapping


@router.get("", response_model=List[EmployeeResponse])
def list_employees(
    department_name: Optional[str] = Query(None),
    active_status: Optional[bool] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    table = get_employee_table(conn)
    query = select(table)

    if department_name is not None:
        query = query.where(table.c.department_name == department_name)
    if active_status is not None:
        query = query.where(table.c.active_status == active_status)

    query = query.limit(limit).offset(offset)
    results = conn.execute(query).all()
    return [row._mapping for row in results]


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(
    employee_id: str,
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    table = get_employee_table(conn)
    result = conn.execute(
        select(table).where(table.c.client_employee_id == employee_id)
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {employee_id} not found",
        )
    return result._mapping


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee(
    employee_id: str,
    employee_update: EmployeeUpdate,
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    table = get_employee_table(conn)
    existing = conn.execute(
        select(table).where(table.c.client_employee_id == employee_id)
    ).first()

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {employee_id} not found",
        )

    update_data = employee_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update",
        )

    update_data["updated_at"] = datetime.utcnow()

    conn.execute(
        update(table)
        .where(table.c.client_employee_id == employee_id)
        .values(**update_data)
    )
    conn.commit()

    result = conn.execute(
        select(table).where(table.c.client_employee_id == employee_id)
    ).first()
    return result._mapping


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: str,
    conn: Connection = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    table = get_employee_table(conn)
    existing = conn.execute(
        select(table).where(table.c.client_employee_id == employee_id)
    ).first()

    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {employee_id} not found",
        )

    conn.execute(
        update(table)
        .where(table.c.client_employee_id == employee_id)
        .values(active_status=False, term_date=datetime.utcnow().date(), updated_at=datetime.utcnow())
    )
    conn.commit()
    return None