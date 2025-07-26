from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models import Document, User
from database import SessionLocal
from routes import routes  # This is your auth routes file

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter()

@router.get("/files/user-documents")
def get_user_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(routes.get_current_user)
):
    docs = db.query(Document).filter(Document.user_email == current_user.email).all()
    return [doc.to_dict() for doc in docs]