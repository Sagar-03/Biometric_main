from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pyotp
import re
from ..utils.auth import (
    verify_password,
    get_password_hash,
    send_otp_email,
    create_access_token,
    assign_role
)
from ..database import get_db
from ..models import User

router = APIRouter()

# ✅ Strong Password Rules
PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@#$%^&+=]).{6,}$"

# ------------------------------------------
# ✅ SIGNUP API (Step 1: Send OTP)
# ------------------------------------------
@router.post("/signup")
async def signup(email: str, password: str, db: Session = Depends(get_db)):
    role = assign_role(email)
    if role is None:
        raise HTTPException(status_code=400, detail="Invalid email. Use a valid @dseu.ac.in email.")

    if not re.match(PASSWORD_REGEX, password):
        raise HTTPException(status_code=400, detail="Password must meet security requirements.")

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    secret = pyotp.random_base32()
    otp = pyotp.TOTP(secret, interval=900).now()
    
    send_otp_email(email, otp)

    new_user = User(
        email=email,
        hashed_password=get_password_hash(password),
        otp_secret=secret,
        otp_expires=datetime.utcnow() + timedelta(minutes=15),
        role=role
    )
    db.add(new_user)
    db.commit()

    return {"message": "OTP sent to email. Please verify."}

# ------------------------------------------
# ✅ LOGIN API
# ------------------------------------------
@router.post("/login")
async def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password.")

    access_token = create_access_token({"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

# ------------------------------------------
# ✅ FORGOT PASSWORD (Step 1: Send OTP)
# ------------------------------------------
@router.post("/forgot-password")
async def forgot_password(email: str, db: Session = Depends(get_db)):
    """Sends an OTP to the user for password reset."""
    if not assign_role(email):
        raise HTTPException(status_code=400, detail="Invalid email. Use an @dseu.ac.in email.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    secret = pyotp.random_base32()
    otp = pyotp.TOTP(secret, interval=900).now()

    user.otp_secret = secret
    user.otp_expires = datetime.utcnow() + timedelta(minutes=15)
    db.commit()

    send_otp_email(email, otp)
    return {"message": "OTP sent to email for password reset."}

# ------------------------------------------
# ✅ VERIFY OTP FOR PASSWORD RESET (Step 2)
# ------------------------------------------
@router.post("/verify-forgot-otp")
async def verify_forgot_otp(email: str, otp: str, db: Session = Depends(get_db)):
    """Verifies OTP for password reset."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.otp_secret:
        raise HTTPException(status_code=400, detail="Invalid request.")

    if user.otp_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired. Request again.")

    totp = pyotp.TOTP(user.otp_secret, interval=900)
    if not totp.verify(otp):
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    user.otp_secret = None
    user.otp_expires = None
    db.commit()

    return {"message": "OTP verified. You can now reset your password."}

# ------------------------------------------
# ✅ RESET PASSWORD (Step 3)
# ------------------------------------------
@router.post("/reset-password")
async def reset_password(email: str, new_password: str, confirm_password: str, db: Session = Depends(get_db)):
    """Resets the user password after OTP verification."""
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    if not re.match(PASSWORD_REGEX, new_password):
        raise HTTPException(status_code=400, detail="Password must meet security requirements.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid request.")

    user.hashed_password = get_password_hash(new_password)
    db.commit()

    return {"message": "Password reset successful. You can now log in."}
