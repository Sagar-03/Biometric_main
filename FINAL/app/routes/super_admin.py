from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..utils.auth import role_required
from ..database import get_db
from ..models import User, Attendance, Campus

router = APIRouter()

# Super Admin: Get all users
@router.get("/users", dependencies=[Depends(role_required(["super_admin"]))])
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

# Super Admin: Add new admin
@router.post("/users/admin", dependencies=[Depends(role_required(["super_admin"]))])
async def create_admin(admin_data: dict, db: Session = Depends(get_db)):
    new_admin = User(**admin_data, role="admin")
    db.add(new_admin)
    db.commit()
    return {"message": "Admin user created successfully"}

# Super Admin: Manage campuses
@router.get("/campuses", dependencies=[Depends(role_required(["super_admin"]))])
async def get_all_campuses(db: Session = Depends(get_db)):
    campuses = db.query(Campus).all()
    return campuses

@router.post("/campuses", dependencies=[Depends(role_required(["super_admin"]))])
async def create_campus(campus_data: dict, db: Session = Depends(get_db)):
    new_campus = Campus(**campus_data)
    db.add(new_campus)
    db.commit()
    return {"message": "Campus created successfully"}

# Super Admin: View all attendance
@router.get("/attendance", dependencies=[Depends(role_required(["super_admin"]))])
async def view_all_attendance(db: Session = Depends(get_db)):
    attendance = db.query(Attendance).all()
    return attendance

# Super Admin: Download global attendance report
@router.get("/attendance/report", dependencies=[Depends(role_required(["super_admin"]))])
async def download_global_attendance_report(db: Session = Depends(get_db)):
    # Logic to generate and return the report
    return {"message": "Global attendance report generated"}
