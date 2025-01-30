from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pyotp
from ..utils.auth import (
    verify_password,
    get_password_hash,
    send_otp_email
)
from ..database import get_db
from ..models import User

router = APIRouter()

@router.post("/forgot-password")
async def forgot_password(employee_id: str, email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.employee_id == employee_id, User.email == email
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee ID and email combination not found"
        )

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret, interval=900)
    otp = totp.now()

    user.reset_token = secret
    user.reset_token_expires = datetime.utcnow() + timedelta(minutes=15)
    db.commit()

    try:
        send_otp_email(email, otp)
    except Exception:
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email"
        )

    return {"message": "OTP sent to your email"}

@router.post("/verify-otp")
async def verify_otp(employee_id: str, email: str, otp: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.employee_id == employee_id, User.email == email
    ).first()

    if not user or not user.reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset request"
        )

    if not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired"
        )

    totp = pyotp.TOTP(user.reset_token, interval=900)
    if not totp.verify(otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )

    return {"message": "OTP verified successfully"}

@router.post("/reset-password")
async def reset_password(employee_id: str, email: str, new_password: str, confirm_password: str, db: Session = Depends(get_db)):
    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
        )

    user = db.query(User).filter(
        User.employee_id == employee_id, User.email == email
    ).first()

    if not user or not user.reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset request"
        )

    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password reset successfully"}