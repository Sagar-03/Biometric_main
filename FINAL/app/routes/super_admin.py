from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from ..utils.auth import role_required, get_current_user
from ..database import get_db
from ..models import User, Attendance, Campus, Leave

router = APIRouter()

# ------------------------------------------
# ✅ VIEW ATTENDANCE (CAMPUS-WISE)
# ------------------------------------------
@router.get("/attendance/campus/{campus_id}", dependencies=[Depends(role_required(["super_admin"]))])
async def view_campus_attendance(
    campus_id: int,
    db: Session = Depends(get_db)
):
    """Fetch attendance for a specific campus"""
    attendance = db.query(Attendance).filter(Attendance.punch_in_campus_id == campus_id).all()

    return [
        {
            "employee_id": record.user_id,
            "name": record.user.full_name,
            "punch_in": record.punch_in,
            "punch_out": record.punch_out,
            "total_hours": record.total_hours,
            "status": record.status
        }
        for record in attendance
    ]

# ------------------------------------------
# ✅ DAILY GEOFENCING VIOLATION REPORT (CAMPUS-WISE)
# ------------------------------------------
@router.get("/attendance/daily-geofencing/campus/{campus_id}")
async def daily_geofencing_report(
    campus_id: int,
    db: Session = Depends(get_db)
):
    """Fetch geofencing violations for today for a specific campus"""
    today = datetime.now().date()
    offenders = db.query(Attendance).filter(
        Attendance.date == today,
        Attendance.total_out_of_bounds_time > 30,
        Attendance.punch_in_campus_id == campus_id
    ).all()

    return [
        {
            "employee_id": record.user_id,
            "name": record.user.full_name,
            "total_out_of_bounds_time": record.total_out_of_bounds_time
        } for record in offenders
    ]

# ------------------------------------------
# ✅ WEEKLY GEOFENCING VIOLATION REPORT (CAMPUS-WISE)
# ------------------------------------------
@router.get("/attendance/weekly-geofencing/campus/{campus_id}")
async def weekly_geofencing_report(
    campus_id: int,
    db: Session = Depends(get_db)
):
    """Fetch weekly geofencing violations for a specific campus"""
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())

    offenders = db.query(Attendance).filter(
        Attendance.date >= start_of_week,
        Attendance.date <= today,
        Attendance.total_out_of_bounds_time > 30,
        Attendance.punch_in_campus_id == campus_id
    ).all()

    return [
        {
            "employee_id": record.user_id,
            "name": record.user.full_name,
            "total_out_of_bounds_time": record.total_out_of_bounds_time
        } for record in offenders
    ]

# ------------------------------------------
# ✅ VIEW & MANAGE LEAVE REQUESTS (ADMIN-LEVEL ONLY)
# ------------------------------------------
@router.get("/leave-requests", dependencies=[Depends(role_required(["super_admin"]))])
async def get_leave_requests(
    db: Session = Depends(get_db)
):
    """Fetch all pending leave requests for Admins (HR or Directors)."""
    leave_requests = db.query(Leave).filter(
        Leave.status == "Pending",
        Leave.user.role == "admin"
    ).all()

    return [
        {
            "id": leave.id,
            "employee_id": leave.user_id,
            "name": leave.user.full_name,
            "leave_type": leave.leave_type,
            "start_date": leave.start_date,
            "end_date": leave.end_date,
            "reason": leave.reason,
            "status": leave.status
        }
        for leave in leave_requests
    ]

@router.post("/leave-requests/{leave_id}/approve")
async def approve_leave_request(
    leave_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Approve an Admin-level leave request."""
    leave = db.query(Leave).filter(Leave.id == leave_id).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    leave.status = "Approved"
    db.commit()
    
    return {"message": "Leave request approved successfully"}

@router.post("/leave-requests/{leave_id}/reject")
async def reject_leave_request(
    leave_id: int, 
    reason: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Reject an Admin-level leave request with a reason."""
    leave = db.query(Leave).filter(Leave.id == leave_id).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    leave.status = "Rejected"
    db.commit()
    
    return {"message": f"Leave request rejected. Reason: {reason}"}

# ------------------------------------------
# ✅ VIEW, CREATE, UPDATE, DELETE CAMPUSES
# ------------------------------------------
@router.get("/campuses", dependencies=[Depends(role_required(["super_admin"]))])
async def get_all_campuses(db: Session = Depends(get_db)):
    """Fetch all campuses"""
    campuses = db.query(Campus).all()
    
    return [
        {
            "id": campus.id,
            "name": campus.name,
            "geo_boundary": campus.geo_boundary
        } for campus in campuses
    ]

@router.post("/campuses", dependencies=[Depends(role_required(["super_admin"]))])
async def create_campus(campus_data: dict, db: Session = Depends(get_db)):
    """Create a new campus"""
    new_campus = Campus(**campus_data)
    db.add(new_campus)
    db.commit()
    
    return {"message": "Campus created successfully"}

@router.put("/campuses/{campus_id}", dependencies=[Depends(role_required(["super_admin"]))])
async def update_campus(campus_id: int, campus_data: dict, db: Session = Depends(get_db)):
    """Update an existing campus"""
    campus = db.query(Campus).filter(Campus.id == campus_id).first()
    
    if not campus:
        raise HTTPException(status_code=404, detail="Campus not found.")

    for key, value in campus_data.items():
        setattr(campus, key, value)
    
    db.commit()
    return {"message": "Campus updated successfully"}

@router.delete("/campuses/{campus_id}", dependencies=[Depends(role_required(["super_admin"]))])
async def delete_campus(campus_id: int, db: Session = Depends(get_db)):
    """Delete a campus"""
    campus = db.query(Campus).filter(Campus.id == campus_id).first()
    
    if not campus:
        raise HTTPException(status_code=404, detail="Campus not found.")

    db.delete(campus)
    db.commit()
    
    return {"message": "Campus deleted successfully"}

# ------------------------------------------
# ✅ SUPER ADMIN: ISSUE RED NOTICE
# ------------------------------------------
@router.post("/attendance/red-notice/{user_id}")
async def issue_red_notice(
    user_id: int, 
    reason: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Issues a red notice for repeated geofencing violations (campus-wise)."""
    user_attendance = db.query(Attendance).filter(
        Attendance.user_id == user_id,
        Attendance.total_out_of_bounds_time > 30
    ).count()

    if user_attendance >= 5:  # If violations occurred for 5+ days
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.red_notice_issued = True
            user.red_notice_reason = reason
            db.commit()
            return {"message": f"Red notice issued to {user.full_name} for repeated geofencing violations."}

    return {"message": "User does not meet red notice criteria yet."}
