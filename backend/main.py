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
        "http://localhost:3001",
        "https://tax-auto-frontend-production.up.railway.app",
        "https://tax-auto-backend-backup-production.up.railway.app",
        # Add specific Railway app URLs as needed
        "*"  # For development - remove in production and specify exact domains
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
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
)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Tax Auto-Fill API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Tax API is running"}

# Add OPTIONS handler for problematic routes
@app.options("/api/auth/register")
async def auth_register_options():
    return JSONResponse(
        status_code=200,
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With",
        }
    )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Global exception: {exc}")
    print(f"Request URL: {request.url}")
    print(f"Request method: {request.method}")
    print(f"Request headers: {dict(request.headers)}")
    print(traceback.format_exc())
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )

# Include routers
try:
    app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
    print("Auth routes included successfully!")
except Exception as e:
    print(f"Error including auth routes: {e}")

try:
    app.include_router(file_routes.router, prefix="/api/files", tags=["files"])
    print("File routes included successfully!")
except Exception as e:
    print(f"Error including file routes: {e}")

try:
    app.include_router(tax_routes.router, prefix="/api/tax", tags=["tax"])
    print("Tax routes included successfully!")
except Exception as e:
    print(f"Error including tax routes: {e}")

try:
    app.include_router(submission_routes.router, prefix="/api/submit", tags=["submission"])
    print("Submission routes included successfully!")
except Exception as e:
    print(f"Error including submission routes: {e}")

try:
    app.include_router(payment_routes.router, prefix="/api/payments", tags=["payments"])
    print("Payment routes included successfully!")
except Exception as e:
    print(f"Error including payment routes: {e}")

try:
    app.include_router(admin_routes.router, prefix="/api/admin", tags=["admin"])
    print("Admin routes included successfully!")
except Exception as e:
    print(f"Error including admin routes: {e}")

print("All routes processing completed!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
