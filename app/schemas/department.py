from pydantic import BaseModel
from typing import Optional


class DepartmentBase(BaseModel):
    name: str
    code: Optional[str] = None
    is_active: Optional[bool] = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentOut(DepartmentBase):
    id: int

    class Config:
        from_attributes = True