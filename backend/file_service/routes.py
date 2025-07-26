from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import uuid4
import os
import json
from database import SessionLocal
from models import Document
from auth.routes import get_current_user
# Replace the mock import with real processor
from .ocr_mock import extract_document_data

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and process document with real OCR"""
    try:
        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Generate unique file ID and save file
        file_id = str(uuid4())
        filename = f"{file_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Save uploaded file
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Extract data using real OCR
        print(f"Processing document: {file.filename}")
        extracted_data = extract_document_data(file_path, file.content_type)
        
        # Save document info to database
        doc = Document(
            id=file_id,
            user_email=current_user.email,
            filename=file.filename,
            file_path=file_path,
            content_type=file.content_type,
            document_type=extracted_data.get("document_type", "Unknown"),
            extracted_data=json.dumps(extracted_data)
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        print(f"Document processed successfully: {extracted_data.get('document_type', 'Unknown')}")
        
        return {
            "id": doc.id,
            "filename": doc.filename,
            "document_type": extracted_data.get("document_type"),
            "extracted_data": extracted_data,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "confidence": extracted_data.get("confidence", 0.0)
        }
        
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/user-documents")
async def get_user_documents(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all documents for the current user with extracted data"""
    try:
        docs = db.query(Document).filter(Document.user_email == current_user.email).all()
        
        documents = []
        for doc in docs:
            # Parse extracted data
            extracted_data = None
            if doc.extracted_data:
                try:
                    extracted_data = json.loads(doc.extracted_data)
                except json.JSONDecodeError:
                    extracted_data = {"error": "Failed to parse extracted data"}
            
            doc_data = {
                "id": doc.id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "upload_date": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "extracted_data": extracted_data,
                "confidence": extracted_data.get("confidence", 0.0) if extracted_data else 0.0
            }
            documents.append(doc_data)
        
        return documents
    except Exception as e:
        print(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@router.get("/download/{document_id}")
async def download_file(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a specific document"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_email == current_user.email
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=doc.file_path,
        filename=doc.filename,
        media_type=doc.content_type
    )

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_email == current_user.email
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    
    # Delete from database
    db.delete(doc)
    db.commit()
    
    return {"message": "Document deleted successfully"}

@router.get("/")
def list_files(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    """Legacy endpoint - redirects to user-documents"""
    return get_user_documents(current_user, db)

@router.get("/ocr-status")
async def check_ocr_status():
    """Check if OCR libraries are available"""
    status = {
        "ocr_available": False,
        "missing_libraries": [],
        "system_info": {}
    }
    
    try:
        import pytesseract
        status["pytesseract"] = "✅ Available"
    except ImportError as e:
        status["missing_libraries"].append(f"pytesseract: {e}")
    
    try:
        import cv2
        status["opencv"] = "✅ Available"
    except ImportError as e:
        status["missing_libraries"].append(f"opencv: {e}")
    
    try:
        from PIL import Image
        status["pillow"] = "✅ Available"
    except ImportError as e:
        status["missing_libraries"].append(f"pillow: {e}")
    
    try:
        import PyPDF2
        status["pypdf2"] = "✅ Available"
    except ImportError as e:
        status["missing_libraries"].append(f"pypdf2: {e}")
    
    try:
        from pdf2image import convert_from_path
        status["pdf2image"] = "✅ Available"
    except ImportError as e:
        status["missing_libraries"].append(f"pdf2image: {e}")
    
    # Check if tesseract executable is available
    try:
        import subprocess
        result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
        status["tesseract_executable"] = f"✅ Available: {result.stdout.split()[1] if result.stdout else 'Unknown version'}"
    except Exception as e:
        status["missing_libraries"].append(f"tesseract executable: {e}")
    
    status["ocr_available"] = len(status["missing_libraries"]) == 0
    
    return status

@router.get("/debug-ocr-public/{document_id}")
async def debug_ocr_extraction_public(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Public debug endpoint to see exactly what OCR is extracting"""
    
    doc = db.query(Document).filter(Document.id == document_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Extract raw text again
        if doc.content_type == "application/pdf":
            # Simple text extraction for debugging
            import PyPDF2
            with open(doc.file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                raw_text = ""
                for page in pdf_reader.pages:
                    raw_text += page.extract_text() + "\n"
        else:
            raw_text = "Non-PDF file - OCR would be used"
        
        # Find all numbers
        import re
        all_numbers = re.findall(r'\d+(?:\.\d{2})?', raw_text)
        
        return {
            "document_id": document_id,
            "filename": doc.filename,
            "raw_text_preview": raw_text[:1000],
            "all_numbers_found": all_numbers[:15],
            "text_lines": raw_text.split('\n')[:15],
            "current_extraction": json.loads(doc.extracted_data) if doc.extracted_data else None
        }
        
    except Exception as e:
        return {"error": str(e), "debug": "Failed to extract"}

@router.post("/force-real-ocr/{document_id}")
async def force_real_ocr(
    document_id: str,
    db: Session = Depends(get_db)
):
    """Force real OCR processing - public version"""
    
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        print("=== FORCING REAL OCR ===")
        
        # Import and create processor directly
        from .ocr_mock import DocumentProcessor
        processor = DocumentProcessor()
        
        # Check OCR availability at processor level
        from .ocr_mock import OCR_AVAILABLE
        print(f"OCR_AVAILABLE in processor: {OCR_AVAILABLE}")
        
        # Force OCR processing
        result = processor.extract_document_data(doc.file_path, doc.content_type)
        
        # Update document
        old_data = json.loads(doc.extracted_data) if doc.extracted_data else {}
        doc.extracted_data = json.dumps(result)
        db.commit()
        
        return {
            "message": "Forced OCR processing completed",
            "document_id": document_id,
            "filename": doc.filename,
            "ocr_available_check": OCR_AVAILABLE,
            "before_extraction": old_data.get("extraction_method", "Unknown"),
            "after_extraction": result.get("extraction_method", "Unknown"),
            "before_wages": old_data.get("wages", "N/A"),
            "after_wages": result.get("wages", "N/A"),
            "debug_info": result.get("debug_info", []),
            "full_result": result
        }
        
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "document_path": doc.file_path,
            "content_type": doc.content_type
        }

@router.get("/documents-public")
async def get_documents_public(db: Session = Depends(get_db)):
    """Get recent documents (public) - for debugging"""
    docs = db.query(Document).order_by(Document.uploaded_at.desc()).limit(5).all()
    
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "upload_date": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "extraction_method": json.loads(doc.extracted_data).get("extraction_method", "Unknown") if doc.extracted_data else "No data"
        }
        for doc in docs
    ]