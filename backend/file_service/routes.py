from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
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

@router.get("/test-ocr-setup")
async def test_ocr_setup():
    """Comprehensive OCR setup test"""
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "ocr_status": "unknown",
        "environment_vars": {},
        "library_status": {},
        "tesseract_info": {},
        "system_info": {},
        "test_results": {}
    }
    
    # Check environment variables
    import os
    status["environment_vars"] = {
        "FORCE_OCR_AVAILABLE": os.environ.get('FORCE_OCR_AVAILABLE', 'not set'),
        "TESSDATA_PREFIX": os.environ.get('TESSDATA_PREFIX', 'not set'),
        "LC_ALL": os.environ.get('LC_ALL', 'not set'),
        "LANG": os.environ.get('LANG', 'not set')
    }
    
    # Test library imports
    libraries = {
        'pytesseract': False,
        'PIL': False,
        'cv2': False,
        'PyPDF2': False,
        'pdf2image': False,
        'numpy': False
    }
    
    for lib_name in libraries:
        try:
            if lib_name == 'pytesseract':
                import pytesseract
                libraries[lib_name] = True
                
                # Test tesseract executable
                try:
                    version = pytesseract.get_tesseract_version()
                    status["tesseract_info"]["version"] = str(version)
                    status["tesseract_info"]["executable_found"] = True
                    
                    # Test available languages
                    try:
                        langs = pytesseract.get_languages()
                        status["tesseract_info"]["languages"] = langs
                    except:
                        status["tesseract_info"]["languages"] = "failed to get"
                        
                except Exception as e:
                    status["tesseract_info"]["error"] = str(e)
                    status["tesseract_info"]["executable_found"] = False
                    
            elif lib_name == 'PIL':
                from PIL import Image
                libraries[lib_name] = True
            elif lib_name == 'cv2':
                import cv2
                libraries[lib_name] = True
                status["library_status"]["opencv_version"] = cv2.__version__
            elif lib_name == 'PyPDF2':
                import PyPDF2
                libraries[lib_name] = True
            elif lib_name == 'pdf2image':
                from pdf2image import convert_from_path
                libraries[lib_name] = True
            elif lib_name == 'numpy':
                import numpy as np
                libraries[lib_name] = True
                status["library_status"]["numpy_version"] = np.__version__
                
        except ImportError as e:
            status["library_status"][f"{lib_name}_error"] = str(e)
    
    status["library_status"]["imports"] = libraries
    
    # Overall OCR availability
    all_required = all(libraries.values())
    tesseract_ok = status["tesseract_info"].get("executable_found", False)
    force_enabled = status["environment_vars"]["FORCE_OCR_AVAILABLE"] == "true"
    
    if all_required and tesseract_ok:
        status["ocr_status"] = "fully_available"
    elif all_required and force_enabled:
        status["ocr_status"] = "forced_available"
    elif all_required:
        status["ocr_status"] = "libraries_ok_tesseract_issue"
    else:
        status["ocr_status"] = "missing_dependencies"
    
    # Test the actual OCR processor
    try:
        from .ocr_mock import OCR_AVAILABLE, processor
        status["test_results"]["processor_ocr_available"] = OCR_AVAILABLE
        status["test_results"]["processor_loaded"] = True
    except Exception as e:
        status["test_results"]["processor_error"] = str(e)
        status["test_results"]["processor_loaded"] = False
    
    # System info
    import platform
    status["system_info"] = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "python_version": platform.python_version()
    }
    
    return status

@router.post("/force-ocr-reprocess/{document_id}")
async def force_ocr_reprocess(
    document_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force reprocess a document with current OCR settings"""
    
    doc = db.query(Document).filter(
        Document.id == document_id,
        Document.user_email == current_user.email
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Save original extraction
        old_data = json.loads(doc.extracted_data) if doc.extracted_data else {}
        
        # Force reprocess
        print(f"=== FORCE REPROCESSING DOCUMENT {document_id} ===")
        new_data = extract_document_data(doc.file_path, doc.content_type)
        
        # Update database
        doc.extracted_data = json.dumps(new_data)
        doc.document_type = new_data.get("document_type", "Unknown")
        db.commit()
        
        return {
            "message": "Document reprocessed successfully",
            "document_id": document_id,
            "filename": doc.filename,
            "before": {
                "extraction_method": old_data.get("extraction_method", "Unknown"),
                "confidence": old_data.get("confidence", 0),
                "wages": old_data.get("wages", "N/A")
            },
            "after": {
                "extraction_method": new_data.get("extraction_method", "Unknown"),
                "confidence": new_data.get("confidence", 0),
                "wages": new_data.get("wages", "N/A")
            },
            "improvement": {
                "method_changed": old_data.get("extraction_method") != new_data.get("extraction_method"),
                "confidence_improved": new_data.get("confidence", 0) > old_data.get("confidence", 0)
            },
            "debug_info": new_data.get("debug_info", []),
            "full_result": new_data
        }
        
    except Exception as e:
        import traceback
        return {
            "error": f"Reprocessing failed: {str(e)}",
            "traceback": traceback.format_exc(),
            "document_id": document_id
        }

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
