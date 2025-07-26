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
    title="Tax Auto-Fill API - Backup",
    description="API for tax document upload, extraction, and filing",
    version="1.0.0"
)

# COMPREHENSIVE CORS SETUP - VERY PERMISSIVE FOR BACKUP
print("🔧 Setting up CORS for backup system...")

# Allow all Railway domains and localhost
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001", 
    "https://tax-auto-frontend-production.up.railway.app",
    "https://tax-auto-frontend-backup-production.up.railway.app",
    "https://tax-auto-backend-production.up.railway.app",
    "https://tax-auto-backend-backup-production.up.railway.app",
]

# Add wildcard Railway patterns
allowed_origins.extend([
    "https://*.railway.app",
    "https://*.up.railway.app",
    "https://tax-auto-frontend-backup-production.up.railway.app",  # Explicit backup frontend
])

print(f"✅ CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "*",
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
)

# Additional manual CORS handling for problematic requests
@app.middleware("http")
async def cors_handler(request: Request, call_next):
    # Handle preflight requests manually
    if request.method == "OPTIONS":
        response = JSONResponse({"message": "OK"})
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
    
    # Process the request
    response = await call_next(request)
    
    # Add CORS headers to all responses
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true" 
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response

# Health check with CORS info
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "Tax API Backup is running",
        "cors_info": "CORS configured for backup frontend"
    }

# CORS test endpoint
@app.get("/cors-test")
async def cors_test():
    return {
        "message": "CORS test successful",
        "backend": "backup",
        "timestamp": "2025-07-26"
    }

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
print("🚀 Backup API server ready with comprehensive CORS support")
