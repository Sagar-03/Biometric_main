from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from ..utils.auth import role_required, get_current_user
from ..database import get_db
from ..models import User, Attendance, Campus, Leave

router = APIRouter()

# ------------------------------------------
# ✅ VIEW ATTENDANCE FOR ASSIGNED CAMPUS
# ------------------------------------------
@router.get("/attendance", dependencies=[Depends(role_required(["admin"]))])
async def get_attendance_for_campus(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Fetch all attendance records for the admin's assigned campus."""
    attendance = db.query(Attendance).filter(
        Attendance.punch_in_campus_id == current_user.campus_id
    ).all()
    
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
# ✅ VIEW USERS (EMPLOYEES) FOR ASSIGNED CAMPUS
# ------------------------------------------
@router.get("/users", dependencies=[Depends(role_required(["admin"]))])
async def get_users_for_campus(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Fetch all employees assigned to the admin's campus."""
    users = db.query(User).filter(User.campus_id == current_user.campus_id).all()
    
    return [
        {
            "employee_id": user.employee_id,
            "name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
        for user in users
    ]

# ------------------------------------------
# ✅ DOWNLOAD CAMPUS ATTENDANCE REPORT
# ------------------------------------------
@router.get("/attendance/report", dependencies=[Depends(role_required(["admin"]))])
async def download_attendance_report_for_campus(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Download a CSV report of attendance for the assigned campus."""
    attendance = db.query(Attendance).filter(
        Attendance.punch_in_campus_id == current_user.campus_id
    ).all()

    def generate_csv():
        yield "Employee ID,Name,Punch In,Punch Out,Total Hours,Status\n"
        for record in attendance:
            yield f"{record.user_id},{record.user.full_name},{record.punch_in},{record.punch_out},{record.total_hours},{record.status}\n"

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=campus_attendance_report.csv"}
    )

# ------------------------------------------
# ✅ DAILY GEO TRACKING VIOLATION REPORT
# ------------------------------------------
@router.get("/attendance/daily-geofencing")
async def daily_geofencing_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch a list of employees who violated geofencing today in admin's assigned campus."""
    today = datetime.now().date()
    offenders = db.query(Attendance).filter(
        Attendance.punch_in_campus_id == current_user.campus_id,
        Attendance.date == today,
        Attendance.total_out_of_bounds_time > 30
    ).all()

    return [
        {
            "employee_id": record.user_id,
            "name": record.user.full_name,
            "total_out_of_bounds_time": record.total_out_of_bounds_time
        } for record in offenders
    ]

# ------------------------------------------
# ✅ WEEKLY GEO TRACKING VIOLATION REPORT
# ------------------------------------------
@router.get("/attendance/weekly-geofencing")
async def weekly_geofencing_report(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch a weekly report of geofencing violations in admin's assigned campus."""
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())

    offenders = db.query(Attendance).filter(
        Attendance.punch_in_campus_id == current_user.campus_id,
        Attendance.date >= start_of_week,
        Attendance.date <= today,
        Attendance.total_out_of_bounds_time > 30
    ).all()

    return [
        {
            "employee_id": record.user_id,
            "name": record.user.full_name,
            "total_out_of_bounds_time": record.total_out_of_bounds_time
        } for record in offenders
    ]

# ------------------------------------------
# ✅ MANAGE LEAVE REQUESTS (Approve/Reject)
# ------------------------------------------
@router.get("/leave-requests", dependencies=[Depends(role_required(["admin"]))])
async def get_leave_requests(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Fetch all pending leave requests for employees in the assigned campus."""
    leave_requests = db.query(Leave).join(User).filter(
        User.campus_id == current_user.campus_id, 
        Leave.status == "Pending"
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
    """Approve a leave request."""
    leave = db.query(Leave).filter(Leave.id == leave_id).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    if leave.user.campus_id != current_user.campus_id:
        raise HTTPException(status_code=403, detail="You can only approve leave requests for your campus.")

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
    """Reject a leave request with a reason."""
    leave = db.query(Leave).filter(Leave.id == leave_id).first()
    
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    if leave.user.campus_id != current_user.campus_id:
        raise HTTPException(status_code=403, detail="You can only reject leave requests for your campus.")

    leave.status = "Rejected"
    db.commit()
    
    return {"message": f"Leave request rejected. Reason: {reason}"}

# ------------------------------------------
# ✅ ADMIN: ISSUE RED NOTICE FOR REPEATED GEOFENCE VIOLATIONS
# ------------------------------------------
@router.post("/attendance/red-notice/{user_id}")
async def issue_red_notice(
    user_id: int, 
    reason: str, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """Issues a red notice if an employee repeatedly violates geofencing rules."""
    user_attendance = db.query(Attendance).filter(
        Attendance.user_id == user_id,
        Attendance.punch_in_campus_id == current_user.campus_id,
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

