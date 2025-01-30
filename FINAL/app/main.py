from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, profile, attendance, admin, super_admin
from .database import engine, Base

app = FastAPI(title="DSEU Dashboard")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with actual frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, tags=["authentication"])
app.include_router(profile.router, tags=["profile"])
app.include_router(attendance.router, tags=["attendance"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(super_admin.router, prefix="/super-admin", tags=["super_admin"])

@app.on_event("startup")
async def startup_event():
    # Create all tables in the database
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
    print("Application started.")

@app.on_event("shutdown")
async def shutdown_event():
    print("Application stopped.")

@app.get("/")
async def root():
    return {"message": "Welcome to the Employee Attendance Dashboard API!"}
