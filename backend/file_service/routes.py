# Add this to your file_service/routes.py

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
