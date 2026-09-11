from sqlalchemy import Column, Integer, String, Date, Time, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(50), default="admin")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        String(50),
        unique=True,
        nullable=False
    )

    name = Column(String(150), nullable=False)

    gender = Column(String(20))

    phone = Column(String(50))

    class_name = Column(String(100))

    attendance = relationship(
        "Attendance",
        back_populates="student",
        cascade="all, delete"
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)

    student_id = Column(
        Integer,
        ForeignKey("students.id")
    )

    date = Column(Date, nullable=False)

    check_in = Column(Time)

    status = Column(
        String(30),
        default="Present"
    )

    note = Column(String(255))

    student = relationship(
        "Student",
        back_populates="attendance"
    )