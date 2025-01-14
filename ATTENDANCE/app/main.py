# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, profile, attendance

app = FastAPI(title="Employee Dashboard")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, tags=["authentication"])
app.include_router(profile.router, tags=["profile"])
app.include_router(attendance.router, tags=["attendance"])

@app.get("/")
async def root():
    return {"message": "Employee Dashboard API"}