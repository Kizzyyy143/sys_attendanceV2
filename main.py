from datetime import date, datetime
from pathlib import Path

from fastapi import (
    FastAPI,
    Request,
    Form,
    Depends
)

from fastapi.responses import (
    HTMLResponse,
    RedirectResponse
)

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from database import (
    Base,
    engine,
    get_db
)

from models import (
    User,
    Student,
    Attendance
)


# ==========================================
# CREATE DATABASE
# ==========================================

Base.metadata.create_all(bind=engine)


# ==========================================
# FASTAPI
# ==========================================

app = FastAPI(
    title="School Attendance System",
    version="1.0.0"
)


# ==========================================
# STATIC
# ==========================================

BASE_DIR = Path(__file__).resolve().parent

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)


# ==========================================
# TEMPLATES
# ==========================================

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)


# ==========================================
# CREATE DEFAULT ADMIN
# ==========================================

def create_default_user():

    db = next(get_db())

    user = db.query(User).filter(
        User.username == "admin"
    ).first()

    if not user:

        user = User(
            username="admin",
            password="admin123",
            role="admin"
        )

        db.add(user)
        db.commit()

    db.close()


create_default_user()


# ==========================================
# HOME
# ==========================================

@app.get("/", response_class=HTMLResponse)
def home():

    return RedirectResponse(
        url="/login",
        status_code=303
    )


# ==========================================
# LOGIN PAGE
# ==========================================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None
        }
    )


# ==========================================
# LOGIN
# ==========================================

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
    "login.html",
    {
        "request": request,
        "error": "Username or password is incorrect!"
    }
)

    response = RedirectResponse(
        url="/dashboard",
        status_code=303
    )

    response.set_cookie(
        key="username",
        value=user.username
    )

    return response


# ==========================================
# LOGOUT
# ==========================================

@app.get("/logout")
def logout():

    response = RedirectResponse(
        url="/login",
        status_code=303
    )

    response.delete_cookie("username")

    return response


# ==========================================
# DASHBOARD
# ==========================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    total_students = db.query(Student).count()

    today = date.today()

    present = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status == "Present"
    ).count()

    absent = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status == "Absent"
    ).count()

    late = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status == "Late"
    ).count()

    leave = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.status == "Leave"
    ).count()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "username": username,
            "total_students": total_students,
            "present": present,
            "absent": absent,
            "late": late,
            "leave": leave,
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
    db: Session = Depends(get_db)
):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    query = db.query(Student)

    if search:

        query = query.filter(
            Student.name.contains(search)
            |
            Student.student_id.contains(search)
        )

    students = query.order_by(
        Student.id.desc()
    ).all()

    return templates.TemplateResponse(
        "students.html",
        {
            "request": request,
            "username": username,
            "students": students,
            "search": search
        }
    )


# ==========================================
# ADD STUDENT PAGE
# ==========================================

@app.get("/students/add", response_class=HTMLResponse)
def add_student_page(request: Request):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    return templates.TemplateResponse(
        "student_form.html",
        {
            "request": request,
            "username": username,
            "student": None,
            "error": None
        }
    )


# ==========================================
# ADD STUDENT
# ==========================================

@app.post("/students/add")
def add_student(
    request: Request,
    student_id: str = Form(...),
    name: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(""),
    class_name: str = Form(""),
    db: Session = Depends(get_db)
):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    exists = db.query(Student).filter(
        Student.student_id == student_id
    ).first()

    if exists:

        return templates.TemplateResponse(
            "student_form.html",
            {
                "request": request,
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

    return RedirectResponse(
        url="/students",
        status_code=303
    )


# ==========================================
# DELETE STUDENT
# ==========================================

@app.get("/students/delete/{student_id}")
def delete_student(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    student = db.query(Student).filter(
        Student.id == student_id
    ).first()

    if student:

        db.delete(student)
        db.commit()

    return RedirectResponse(
        url="/students",
        status_code=303
    )


# ==========================================
# ATTENDANCE PAGE
# ==========================================

@app.get("/attendance", response_class=HTMLResponse)
def attendance_page(
    request: Request,
    db: Session = Depends(get_db)
):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    students = db.query(Student).order_by(
        Student.name
    ).all()

    today = date.today()

    records = db.query(Attendance).filter(
        Attendance.date == today
    ).all()

    attendance_map = {
        record.student_id: record.status
        for record in records
    }

    return templates.TemplateResponse(
        "attendance.html",
        {
            "request": request,
            "username": username,
            "students": students,
            "today": today,
            "attendance_map": attendance_map
        }
    )


# ==========================================
# SAVE ATTENDANCE
# ==========================================

@app.post("/attendance")
async def save_attendance(
    request: Request,
    db: Session = Depends(get_db)
):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    form = await request.form()

    today = date.today()

    students = db.query(Student).all()

    for student in students:

        status = form.get(
            f"status_{student.id}"
        )

        if not status:
            status = "Absent"

        record = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.date == today
        ).first()

        if record:

            record.status = status

            if status == "Present":

                record.check_in = datetime.now().time()

        else:

            record = Attendance(
                student_id=student.id,
                date=today,
                check_in=(
                    datetime.now().time()
                    if status == "Present"
                    else None
                ),
                status=status
            )

            db.add(record)

    db.commit()

    return RedirectResponse(
        url="/attendance",
        status_code=303
    )


# ==========================================
# HISTORY
# ==========================================

@app.get("/history", response_class=HTMLResponse)
def history(
    request: Request,
    selected_date: str = "",
    db: Session = Depends(get_db)
):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    if selected_date:

        try:
            selected = datetime.strptime(
                selected_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            selected = date.today()

    else:

        selected = date.today()

    records = db.query(Attendance).filter(
        Attendance.date == selected
    ).order_by(
        Attendance.id.desc()
    ).all()

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "username": username,
            "records": records,
            "selected_date": selected
        }
    )


# ==========================================
# REPORTS
# ==========================================

@app.get("/reports", response_class=HTMLResponse)
def reports(
    request: Request,
    db: Session = Depends(get_db)
):

    username = request.cookies.get("username")

    if not username:
        return RedirectResponse(
            url="/login",
            status_code=303
        )

    total = db.query(Attendance).count()

    present = db.query(Attendance).filter(
        Attendance.status == "Present"
    ).count()

    absent = db.query(Attendance).filter(
        Attendance.status == "Absent"
    ).count()

    late = db.query(Attendance).filter(
        Attendance.status == "Late"
    ).count()

    leave = db.query(Attendance).filter(
        Attendance.status == "Leave"
    ).count()

    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "username": username,
            "total": total,
            "present": present,
            "absent": absent,
            "late": late,
            "leave": leave
        }
    )