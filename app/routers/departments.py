from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentOut

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post("/", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
def create_department(department: DepartmentCreate, db: Session = Depends(get_db)):
    existing = db.query(Department).filter(Department.name == department.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Department {department.name} already exists")

    new_department = Department(**department.model_dump())
    db.add(new_department)
    db.commit()
    db.refresh(new_department)
    return new_department


@router.get("/", response_model=List[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()


@router.get("/{department_id}", response_model=DepartmentOut)
def get_department(department_id: int, db: Session = Depends(get_db)):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department