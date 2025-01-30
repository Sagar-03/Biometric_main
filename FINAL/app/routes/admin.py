from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..utils.auth import role_required, get_current_user
from ..database import get_db
from ..models import User, Attendance

router = APIRouter()

# Admin: View attendance for assigned campus
@router.get("/attendance", dependencies=[Depends(role_required(["admin"]))])
async def get_attendance_for_campus(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    attendance = db.query(Attendance).filter(
        Attendance.punch_in_campus_id == current_user.campus_id
    ).all()
    return attendance

# Admin: Manage users for assigned campus
@router.get("/users", dependencies=[Depends(role_required(["admin"]))])
async def get_users_for_campus(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    users = db.query(User).filter(User.campus_id == current_user.campus_id).all()
    return users

# Admin: Download attendance report for assigned campus
@router.get("/attendance/report", dependencies=[Depends(role_required(["admin"]))])
async def download_attendance_report_for_campus(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    attendance = db.query(Attendance).filter(
        Attendance.punch_in_campus_id == current_user.campus_id
    ).all()
    # Logic to generate and return the report
    return {"message": "Report generated for campus attendance"}
