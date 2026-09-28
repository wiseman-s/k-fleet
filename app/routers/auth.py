from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="office_login.html",
        context={"error": None}
    )


@router.post("/login")
def login(
    request: Request,
    staff_number: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.staff_number == staff_number).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="office_login.html",
            context={"error": "Invalid staff number or password"},
            status_code=401
        )

    if user.role == "gatekeeper":
        return templates.TemplateResponse(
            request=request,
            name="office_login.html",
            context={"error": "Gate accounts cannot access the office system. Use the gate app."},
            status_code=403
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="office_login.html",
            context={"error": "Account is disabled"},
            status_code=403
        )

    token = create_access_token({"sub": str(user.id), "role": user.role})

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="kfleet_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("kfleet_token")
    return response


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_first_admin(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.staff_number == user_data.staff_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Staff number already registered")

    total = db.query(User).count()
    role = "admin" if total == 0 else user_data.role

    new_user = User(
        staff_number=user_data.staff_number,
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        role=role,
        station_id=user_data.station_id,
        driver_id=user_data.driver_id,
        password_hash=hash_password(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user