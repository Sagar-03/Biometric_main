from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import pyotp

from ..database import get_db
from ..models import User
from ..utils.auth import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    send_otp_email
)

router = APIRouter()

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.employee_id == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect employee ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect employee ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)  # You can adjust this value
    access_token = create_access_token(
        data={"sub": user.employee_id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password")
async def forgot_password(email: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate OTP
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret, interval=900)  # 15 minutes validity
    otp = totp.now()
    
    # Store OTP secret in database
    user.reset_token = secret
    user.reset_token_expires = datetime.utcnow() + timedelta(minutes=15)
    db.commit()
    
    # Send OTP via email
    try:
        send_otp_email(email, otp)
    except Exception as e:
        # Reset the user's token if email fails
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send OTP email"
        )
    
    return {"message": "OTP sent to your email"}

@router.post("/reset-password")
async def reset_password(
    email: str,
    otp: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset request"
        )
    
    if not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        # Clear expired token
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired"
        )
    
    # Verify OTP
    totp = pyotp.TOTP(user.reset_token, interval=900)
    if not totp.verify(otp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    # Update password
    user.hashed_password = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.first_login = False
    db.commit()
    
    return {"message": "Password reset successfully"}