from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import uuid4
import json
from database import SessionLocal
from models import TaxSubmission
from auth.routes import get_current_user

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SubmissionRequest(BaseModel):
    form_data: dict
    tax_calculation: dict = None
    filing_type: str

@router.post("/")
def submit_tax_return(
    req: SubmissionRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    submission_id = str(uuid4())
    submission = TaxSubmission(
        id=submission_id,
        user_email=current_user.email,
        form_data=json.dumps(req.form_data),
        status="submitted",
        tax_owed=req.tax_calculation.get("tax_owed", 0) if req.tax_calculation else 0,
        refund_amount=req.tax_calculation.get("refund", 0) if req.tax_calculation else 0
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return {
        "id": submission.id,
        "status": submission.status,
        "tax_owed": submission.tax_owed,
        "refund_amount": submission.refund_amount
    }