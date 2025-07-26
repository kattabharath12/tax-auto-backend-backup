from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback
import os

from auth import routes as auth_routes
from file_service import routes as file_routes
from tax_engine import routes as tax_routes
from submission import routes as submission_routes
from payment import routes as payment_routes
from admin import routes as admin_routes

# Database setup
from database import engine
from models import Base

try:
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
except Exception as e:
    print(f"Database setup error: {e}")

app = FastAPI(
    title="Tax Auto-Fill API",
    description="API for tax document upload, extraction, and filing",
    version="1.0.0"
)

# Enhanced CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://tax-auto-frontend-production.up.railway.app",
        "https://*.railway.app",
        "https://*.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Tax API is running"}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global exception: {exc}")
    print(traceback.format_exc())
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Include routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(file_routes.router, prefix="/api/files", tags=["files"])
app.include_router(tax_routes.router, prefix="/api/tax", tags=["tax"])
app.include_router(submission_routes.router, prefix="/api/submit", tags=["submission"])
app.include_router(payment_routes.router, prefix="/api/payments", tags=["payments"])
app.include_router(admin_routes.router, prefix="/api/admin", tags=["admin"])

print("All routes included successfully!")