from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import shutil
import os
from ..utils.auth import get_current_user
from ..database import get_db
from ..models import User
router = APIRouter()

@router.get("/profile/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "employee_id": current_user.employee_id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "profile_picture": current_user.profile_picture,
        "role": current_user.role
    }

@router.put("/profile/update")
async def update_profile(
    full_name: Optional[str] = None,
    profile_picture: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if full_name:
        current_user.full_name = full_name
    
    if profile_picture:
        # Save profile picture
        file_location = f"media/profile_pictures/{current_user.employee_id}.jpg"
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(profile_picture.file, file_object)
        current_user.profile_picture = file_location
    
    db.commit()
    return {"message": "Profile updated successfully"}