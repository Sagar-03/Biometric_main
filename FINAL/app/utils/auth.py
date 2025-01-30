import os
import logging
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..models import User
from ..database import get_db
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from shapely.geometry import Point, Polygon

# Email & JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your_default_secret_key")
ALGORITHM = "HS256"
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Logger Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------------------
# ✅ PASSWORD HASHING & VERIFICATION
# ------------------------------------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# ------------------------------------------
# ✅ EMAIL OTP FUNCTION FOR FORGOT PASSWORD
# ------------------------------------------
def send_otp_email(recipient_email: str, otp: str):
    try:
        message = MIMEMultipart()
        message["From"] = EMAIL_USERNAME
        message["To"] = recipient_email
        message["Subject"] = "Your OTP for Password Reset"

        body = (
            f"Hello,\n\n"
            f"Your OTP for password reset is: {otp}.\n"
            f"It is valid for the next 15 minutes.\n\n"
            f"Regards,\nYour Team"
        )
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(message)

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending email, please try again later."
        )

# ------------------------------------------
# ✅ AUTHENTICATION: GET CURRENT USER
# ------------------------------------------
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        employee_id: str = payload.get("sub")
        if employee_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.employee_id == employee_id).first()
    if user is None:
        raise credentials_exception
    return user

# ------------------------------------------
# ✅ ROLE-BASED ACCESS CONTROL
# ------------------------------------------
def role_required(required_roles: list):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permissions."
            )
        return current_user
    return role_checker

# ------------------------------------------
# ✅ CHECK IF USER IS WITHIN A CAMPUS GEOFENCE
# ------------------------------------------
def check_within_geofence(latitude: float, longitude: float, geo_boundary: str):
    if not geo_boundary:
        return False
    boundary_points = [tuple(map(float, coord.split(','))) for coord in geo_boundary.split(';')]
    polygon = Polygon(boundary_points)
    point = Point(latitude, longitude)
    return polygon.contains(point)
