from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100))
    profile_picture = Column(Text, nullable=True)
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    first_login = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    attendance_records = relationship("Attendance", back_populates="user")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime, server_default=func.now())
    punch_in = Column(DateTime)
    punch_out = Column(DateTime, nullable=True)
    total_hours = Column(Float, nullable=True)
    status = Column(String(50))  # Present/Absent/On-duty/On-leave
    punch_in_campus_id = Column(Integer, ForeignKey("campuses.id"))
    punch_out_campus_id = Column(Integer, ForeignKey("campuses.id"), nullable=True)

    user = relationship("User", back_populates="attendance_records")
    punch_in_campus = relationship("Campus", foreign_keys=[punch_in_campus_id])
    punch_out_campus = relationship("Campus", foreign_keys=[punch_out_campus_id])


class Campus(Base):
    __tablename__ = "campuses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True)
    geo_boundary = Column(Text)
