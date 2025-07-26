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

# ULTRA-PERMISSIVE CORS - GUARANTEED TO WORK
print("🔧 Setting up ULTRA-PERMISSIVE CORS...")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow ALL origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow ALL methods
    allow_headers=["*"],  # Allow ALL headers
    expose_headers=["*"]  # Expose ALL headers
)

print("✅ CORS configured with wildcard permissions")

# Manual CORS headers for extra safety
@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    response = await call_next(request)
    
    # Add explicit CORS headers to every response
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Expose-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    
    return response

# Handle OPTIONS requests explicitly
@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    response = JSONResponse({"message": "OK"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Health check with CORS confirmation
@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "message": "Tax API Backup is running",
        "cors_status": "ULTRA-PERMISSIVE ENABLED",
        "timestamp": "2025-07-26"
    }

# CORS test endpoint
@app.get("/cors-test")
async def cors_test(request: Request):
    origin = request.headers.get("origin", "no-origin")
    return {
        "message": "CORS test successful",
        "backend": "backup",
        "origin_received": origin,
        "cors_enabled": True,
        "timestamp": "2025-07-26"
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global exception: {exc}")
    print(traceback.format_exc())
    
    if isinstance(exc, HTTPException):
        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    else:
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
    
    # Add CORS headers to error responses too
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    
    return response

# Include routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(file_routes.router, prefix="/api/files", tags=["files"])
app.include_router(tax_routes.router, prefix="/api/tax", tags=["tax"])
app.include_router(submission_routes.router, prefix="/api/submit", tags=["submission"])
app.include_router(payment_routes.router, prefix="/api/payments", tags=["payments"])
app.include_router(admin_routes.router, prefix="/api/admin", tags=["admin"])

print("All routes included successfully!")
print("🚀 Backup API server ready with ULTRA-PERMISSIVE CORS support")
print("🔥 CORS will work with ANY frontend domain")
