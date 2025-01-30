from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
from shapely.geometry import Point, Polygon
from sqlalchemy.sql import func
from fastapi.responses import StreamingResponse
from ..utils.auth import get_current_user ,check_within_geofence
from ..database import get_db
from ..models import Attendance, Campus, User

router = APIRouter()

# Helper function: Check if location is within geofence
# def check_within_geofence(lat, lng, geo_boundary):
#     boundary_points = [tuple(map(float, coord.split(','))) for coord in geo_boundary.split(';')]
#     polygon = Polygon(boundary_points)
#     point = Point(lat, lng)
#     return polygon.contains(point)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
from sqlalchemy.sql import func
from fastapi.responses import StreamingResponse
from shapely.geometry import Point, Polygon
from ..utils.auth import get_current_user, check_within_geofence
from ..database import get_db
from ..models import Attendance, Campus, User

router = APIRouter()


@router.post("/attendance/punch-in")
async def punch_in(
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now(pytz.UTC).date()

    # Check for existing punch-in
    existing_attendance = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.date) == today
    ).first()

    if existing_attendance and existing_attendance.punch_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already punched in today"
        )

    # Identify the campus
    campuses = db.query(Campus).all()
    for campus in campuses:
        if check_within_geofence(latitude, longitude, campus.geo_boundary):
            attendance = Attendance(
                user_id=current_user.id,
                punch_in=datetime.now(pytz.UTC),
                punch_in_campus_id=campus.id,
                status="Present"
            )
            db.add(attendance)
            db.commit()
            return {"message": f"Punched in at {campus.name}", "status": "success"}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Punch-in location outside campus geofence"
    )


@router.post("/attendance/punch-out")
async def punch_out(
    latitude: float,
    longitude: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now(pytz.UTC).date()

    # Find the user's punch-in record for today
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

    # Identify the campus
    campuses = db.query(Campus).all()
    for campus in campuses:
        if check_within_geofence(latitude, longitude, campus.geo_boundary):
            attendance.punch_out = datetime.now(pytz.UTC)
            attendance.punch_out_campus_id = campus.id
            attendance.total_hours = (attendance.punch_out - attendance.punch_in).total_seconds() / 3600
            db.commit()
            return {
                "message": f"Punched out at {campus.name}",
                "total_hours": attendance.total_hours,
                "status": "success"
            }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Punch-out location outside campus geofence"
    )


@router.get("/attendance/daily-status")
async def get_daily_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now(pytz.UTC).date()
    attendance = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.date) == today
    ).first()

    if not attendance:
        return {"status": "Absent"}

    return {
        "date": today,
        "punch_in": attendance.punch_in,
        "punch_out": attendance.punch_out,
        "total_hours": attendance.total_hours,
        "status": attendance.status
    }

@router.get("/attendance/weekly-status")
async def get_weekly_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now(pytz.UTC).date()
    start_of_week = today - timedelta(days=today.weekday())

    weekly_records = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        Attendance.date >= start_of_week,
        Attendance.date <= today
    ).all()

    weekly_data = []
    for record in weekly_records:
        weekly_data.append({
            "date": record.date,
            "punch_in": record.punch_in,
            "punch_out": record.punch_out,
            "total_hours": record.total_hours,
            "status": record.status
        })

    return {
        "start_of_week": start_of_week,
        "end_of_week": today,
        "records": weekly_data
    }

@router.get("/attendance/progress")
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now(pytz.UTC).date()
    start_of_week = today - timedelta(days=today.weekday())

    # Fetch today's attendance
    today_record = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        func.date(Attendance.date) == today
    ).first()

    # Fetch weekly attendance
    weekly_records = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        Attendance.date >= start_of_week,
        Attendance.date <= today
    ).all()

    # Daily progress
    daily_hours = (
        (today_record.punch_out - today_record.punch_in).total_seconds() / 3600
        if today_record and today_record.punch_in and today_record.punch_out
        else 0
    )
    remaining_daily = max(0, 8 - daily_hours)

    # Weekly progress
    total_weekly_hours = sum(
        (record.punch_out - record.punch_in).total_seconds() / 3600
        for record in weekly_records
        if record.punch_in and record.punch_out
    )
    remaining_weekly = max(0, 40 - total_weekly_hours)

    return {
        "daily": {
            "completed_hours": daily_hours,
            "remaining_hours": remaining_daily,
        },
        "weekly": {
            "completed_hours": total_weekly_hours,
            "remaining_hours": remaining_weekly,
        },
    }

@router.get("/attendance/download-report")
async def download_report(
    start_date: datetime,
    end_date: datetime,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = db.query(Attendance).filter(
        Attendance.user_id == current_user.id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    def generate_csv():
        yield "Date,Punch In,Punch Out,Hours Worked,Status\n"
        for record in records:
            yield f"{record.date},{record.punch_in},{record.punch_out},{record.total_hours},{record.status}\n"

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_report.csv"}
    )
