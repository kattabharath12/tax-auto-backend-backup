from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    name = Column(String)
    ssn = Column(String)
    dob = Column(String)
    address = Column(Text)
    state = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True)
    user_email = Column(String, index=True)
    filename = Column(String)
    file_path = Column(String)
    content_type = Column(String)
    document_type = Column(String)  # W-2, 1099-NEC, W-9, etc.
    extracted_data = Column(Text)  # JSON string
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_path": self.file_path,
            "content_type": self.content_type,
            "document_type": self.document_type,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

class TaxSubmission(Base):
    __tablename__ = "tax_submissions"
    id = Column(String, primary_key=True, index=True)
    user_email = Column(String, index=True)
    form_data = Column(Text)  # JSON string
    status = Column(String, default="pending")
    submitted_at = Column(DateTime, default=datetime.utcnow)
    tax_owed = Column(Float, default=0.0)
    refund_amount = Column(Float, default=0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "user_email": self.user_email,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "tax_owed": self.tax_owed,
            "refund_amount": self.refund_amount,
        }

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, index=True)
    user_email = Column(String, index=True)
    submission_id = Column(String)
    amount = Column(Float)
    status = Column(String, default="pending")
    payment_method = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "submission_id": self.submission_id,
            "amount": self.amount,
            "status": self.status,
            "payment_method": self.payment_method,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class W9Form(Base):
    __tablename__ = "w9_forms"
    id = Column(String, primary_key=True, index=True)
    user_email = Column(String, index=True)
    document_id = Column(String)  # Reference to Document table
    name = Column(String)
    business_name = Column(String)
    tax_classification = Column(String)
    address = Column(Text)
    taxpayer_id = Column(String)
    ein = Column(String)
    ssn = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "name": self.name,
            "business_name": self.business_name,
            "tax_classification": self.tax_classification,
            "address": self.address,
            "taxpayer_id": self.taxpayer_id,
            "ein": self.ein,
            "ssn": self.ssn,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }