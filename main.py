from datetime import date, datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import User, Student, Attendance

BASE_DIR = Path(__file__).resolve().parent


# ==========================================
# CUSTOM REDIRECT EXCEPTION FOR AUTH
# ==========================================

class AuthRequiredException(Exception):
    """Custom exception raised when an unauthenticated user accesses protected routes."""
    pass


# ==========================================
# LIFESPAN (APP STARTUP / SHUTDOWN)
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = User(
                username="admin",
                password="admin123",
                role="admin"
            )
            db.add(user)
            db.commit()
    yield


# ==========================================
# FASTAPI APP SETUP
# ==========================================

app = FastAPI(
    title="School Attendance System",
    version="1.0.0",
    lifespan=lifespan
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")


# ==========================================
# AUTHENTICATION DEPENDENCY
# ==========================================

def get_current_user(request: Request) -> str:
    username = request.cookies.get("username")
    if not username:
        raise AuthRequiredException()
    return username


@app.exception_handler(AuthRequiredException)
async def auth_required_handler(request: Request, exc: AuthRequiredException):
    return RedirectResponse(url="/login", status_code=303)


# ==========================================
# HOME & LOGIN
# ==========================================

@app.get("/", response_class=HTMLResponse)
def home():
    return RedirectResponse(url="/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None}
    )


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.username == username,
        User.password == password
    ).first()

    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Username or password is incorrect!"}
        )

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="username",
        value=user.username,
        httponly=True,
        samesite="lax"
    )
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("username")
    return response


# ==========================================
# DASHBOARD
# ==========================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    today = date.today()
    total_students = db.query(Student).count()

    status_counts = db.query(
        Attendance.status,
        func.count(Attendance.id)
    ).filter(
        Attendance.date == today
    ).group_by(Attendance.status).all()

    counts_dict = dict(status_counts)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "username": username,
            "total_students": total_students,
            "present": counts_dict.get("Present", 0),
            "absent": counts_dict.get("Absent", 0),
            "late": counts_dict.get("Late", 0),
            "leave": counts_dict.get("Leave", 0),
            "today": today
        }
    )


# ==========================================
# STUDENTS
# ==========================================

@app.get("/students", response_class=HTMLResponse)
def students(
    request: Request,
    search: str = "",
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    query = db.query(Student)

    if search:
        query = query.filter(
            or_(
                Student.name.contains(search),
                Student.student_id.contains(search)
            )
        )

    students_list = query.order_by(Student.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "username": username,
            "students": students_list,
            "search": search
        }
    )


@app.get("/students/add", response_class=HTMLResponse)
def add_student_page(
    request: Request,
    username: str = Depends(get_current_user)
):
    return templates.TemplateResponse(
        request=request,
        name="student_form.html",
        context={
            "username": username,
            "student": None,
            "error": None
        }
    )


@app.post("/students/add")
def add_student(
    request: Request,
    student_id: str = Form(...),
    name: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    class_name: str = Form(""),
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    exists = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if exists:
        return templates.TemplateResponse(
            request=request,
            name="student_form.html",
            context={
                "username": username,
                "student": None,
                "error": "Student ID already exists!"
            }
        )

    student = Student(
        student_id=student_id,
        name=name,
        gender=gender,
        phone=phone,
        class_name=class_name
    )

    db.add(student)
    db.commit()

    return RedirectResponse(url="/students", status_code=303)


# ==========================================
# EDIT STUDENT PAGE
# ==========================================

@app.get("/students/edit/{db_id}", response_class=HTMLResponse)
def edit_student_page(
    db_id: int,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == db_id).first()
    if not student:
        return RedirectResponse(url="/students", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="student_form.html",
        context={
            "username": username,
            "student": student,
            "error": None
        }
    )


# ==========================================
# EDIT STUDENT ACTION
# ==========================================

@app.post("/students/edit/{db_id}")
def edit_student(
    db_id: int,
    request: Request,
    student_id: str = Form(...),
    name: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    class_name: str = Form(""),
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == db_id).first()
    if not student:
        return RedirectResponse(url="/students", status_code=303)

    # Prevent assigning a Student ID that belongs to another student
    exists = db.query(Student).filter(
        Student.student_id == student_id,
        Student.id != db_id
    ).first()

    if exists:
        return templates.TemplateResponse(
            request=request,
            name="student_form.html",
            context={
                "username": username,
                "student": student,
                "error": "Student ID already exists for another student!"
            }
        )

    # Update attributes
    student.student_id = student_id
    student.name = name
    student.gender = gender
    student.phone = phone
    student.class_name = class_name

    db.commit()

    return RedirectResponse(url="/students", status_code=303)


# ==========================================
# DELETE STUDENT
# ==========================================

@app.get("/students/delete/{db_id}")
def delete_student(
    db_id: int,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    student = db.query(Student).filter(Student.id == db_id).first()

    if student:
        db.delete(student)
        db.commit()

    return RedirectResponse(url="/students", status_code=303)


# ==========================================
# ATTENDANCE
# ==========================================

@app.get("/attendance", response_class=HTMLResponse)
def attendance_page(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    students_list = db.query(Student).order_by(Student.name).all()
    today = date.today()

    records = db.query(Attendance).filter(
        Attendance.date == today
    ).all()

    attendance_map = {record.student_id: record.status for record in records}

    return templates.TemplateResponse(
        request=request,
        name="attendance.html",
        context={
            "username": username,
            "students": students_list,
            "today": today,
            "attendance_map": attendance_map
        }
    )


@app.post("/attendance")
async def save_attendance(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    form = await request.form()
    today = date.today()
    students_list = db.query(Student).all()

    existing_records = db.query(Attendance).filter(
        Attendance.date == today
    ).all()
    records_map = {record.student_id: record for record in existing_records}

    now_time = datetime.now().time()

    for student in students_list:
        status = form.get(f"status_{student.id}") or "Absent"
        record = records_map.get(student.id)

        if record:
            record.status = status
            if status == "Present" and not record.check_in:
                record.check_in = now_time
        else:
            record = Attendance(
                student_id=student.id,
                date=today,
                check_in=now_time if status == "Present" else None,
                status=status
            )
            db.add(record)

    db.commit()
    return RedirectResponse(url="/attendance", status_code=303)


# ==========================================
# HISTORY & REPORTS
# ==========================================

@app.get("/history", response_class=HTMLResponse)
def history(
    request: Request,
    selected_date: str = "",
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    selected = date.today()
    if selected_date:
        try:
            selected = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            pass

    records = db.query(Attendance).filter(
        Attendance.date == selected
    ).order_by(Attendance.id.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "username": username,
            "records": records,
            "selected_date": selected
        }
    )


@app.get("/reports", response_class=HTMLResponse)
def reports(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_user)
):
    total = db.query(Attendance).count()

    status_counts = db.query(
        Attendance.status,
        func.count(Attendance.id)
    ).group_by(Attendance.status).all()

    counts_dict = dict(status_counts)

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "username": username,
            "total": total,
            "present": counts_dict.get("Present", 0),
            "absent": counts_dict.get("Absent", 0),
            "late": counts_dict.get("Late", 0),
            "leave": counts_dict.get("Leave", 0)
        }
    )