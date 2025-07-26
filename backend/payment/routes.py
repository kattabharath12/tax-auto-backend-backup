from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from database import SessionLocal
from models import Payment
from auth.routes import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PaymentRequest(BaseModel):
    amount: float
    payment_method: str

@router.post("/charge")
def make_payment(
    req: PaymentRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    payment_id = str(uuid4())
    payment = Payment(
        id=payment_id,
        user_email=current_user.email,
        amount=req.amount,
        status="success",
        payment_method=req.payment_method,
        created_at=datetime.utcnow()
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {"id": payment.id, "status": payment.status, "message": "Payment successful"}

@router.get("/")
def list_payments(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    payments = db.query(Payment).filter(Payment.user_email == current_user.email).all()
    return {
        "payments": [
            {
                "id": p.id,
                "amount": p.amount,
                "status": p.status,
                "payment_method": p.payment_method,
                "created_at": p.created_at
            } for p in payments
        ]
    }
# ADD THIS TO payment/routes.py
@router.get("/history")
def get_payment_history(
    current_user = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Get payment history for current user"""
    try:
        payments = db.query(Payment).filter(Payment.user_email == current_user.email).all()
        
        return [
            {
                "id": p.id,
                "amount": p.amount,
                "status": p.status,
                "payment_method": p.payment_method,
                "payment_date": p.created_at.isoformat() if p.created_at else None,
                "transaction_id": f"txn_{p.id[:8]}",
                "description": "Tax Payment"
            } for p in payments
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch payment history: {str(e)}")