from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import TaxSubmission, Payment
from auth.routes import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_admin(user):
    # For demo, treat the first registered user as admin
    return user.email.endswith("@admin.com") or user.email == "admin@example.com"

@router.get("/submissions")
def get_all_submissions(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_admin(current_user):
        return {"error": "Admin access required"}
    subs = db.query(TaxSubmission).all()
    return {
        "submissions": [
            {
                "id": s.id,
                "user_email": s.user_email,
                "status": s.status,
                "submitted_at": s.submitted_at,
                "filing_type": s.form_data,
                "tax_owed": s.tax_owed,
                "refund_amount": s.refund_amount
            } for s in subs
        ]
    }

@router.get("/payments")
def get_all_payments(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_admin(current_user):
        return {"error": "Admin access required"}
    pays = db.query(Payment).all()
    return {
        "payments": [
            {
                "id": p.id,
                "user_email": p.user_email,
                "amount": p.amount,
                "status": p.status,
                "payment_method": p.payment_method,
                "created_at": p.created_at
            } for p in pays
        ]
    }

@router.get("/stats")
def get_stats(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    if not is_admin(current_user):
        return {"error": "Admin access required"}
    total_submissions = db.query(TaxSubmission).count()
    total_payments = db.query(Payment).count()
    return {
        "total_submissions": total_submissions,
        "total_payments": total_payments,
        "submission_stats": {},
        "payment_stats": {}
    }
# ADD THIS TO admin/routes.py
@router.get("/users")
def get_all_users(
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Get all users for admin"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name or "N/A",
            "state": u.state or "N/A",
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "is_active": getattr(u, 'is_active', True)
        } for u in users
    ]