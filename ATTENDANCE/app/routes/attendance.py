from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
from ..utils.auth import get_current_user
from ..database import get_db
from ..models import User , Attendance

router = APIRouter()

@router.post("/attendance/punch-in")
async def punch_in(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if already punched in today
    today = datetime.now(pytz.UTC).date()
    existing_attendance = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.date) == today
    ).first()
    
    if existing_attendance and existing_attendance.punch_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already punched in today"
        )
    
    # Create new attendance record
    attendance = Attendance(
        user_id=current_user.id,
        punch_in=datetime.now(pytz.UTC),
        status="Present"
    )
    db.add(attendance)
    db.commit()
    
    return {"message": "Punched in successfully"}

@router.post("/attendance/punch-out")
async def punch_out(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now(pytz.UTC).date()
    attendance = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.date) == today
    ).first()
    
    if not attendance or not attendance.punch_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No punch-in record found for today"
        )
    
    if attendance.punch_out:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already punched out today"
        )
    
    attendance.punch_out = datetime.now(pytz.UTC)
    attendance.total_hours = (attendance.punch_out - attendance.punch_in).total_seconds() / 3600
    db.commit()
    
    return {"message": "Punched out successfully"}

@router.get("/attendance/report")
async def get_attendance_report(
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    attendance_records = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()
    
    return {
        "records": [
            {
                "date": record.date,
                "punch_in": record.punch_in,
                "punch_out": record.punch_out,
                "total_hours": record.total_hours,
                "status": record.status
            }
            for record in attendance_records
        ]
    }