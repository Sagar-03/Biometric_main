from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    profile_picture = Column(String, nullable=True)
    role = Column(String)
    is_active = Column(Boolean, default=True)
    first_login = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    attendance_records = relationship("Attendance", back_populates="user")

class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime(timezone=True), server_default=func.now())
    punch_in = Column(DateTime(timezone=True))
    punch_out = Column(DateTime(timezone=True), nullable=True)
    total_hours = Column(Float, nullable=True)
    status = Column(String)  # Present/Absent/On-duty/On-leave
    
    user = relationship("User", back_populates="attendance_records")
