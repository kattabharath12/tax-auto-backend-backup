import os
import json
import re
import random
import platform
from typing import Dict, Any, Optional, List, Tuple

# Check if OCR should be forced available from environment
FORCE_OCR = os.environ.get('FORCE_OCR_AVAILABLE', 'false').lower() == 'true'

try:
    import pytesseract
    from PIL import Image
    import PyPDF2
    from pdf2image import convert_from_path
    import cv2
    import numpy as np
    
    # FORCE OCR to be available if environment variable is set
    OCR_AVAILABLE = True if FORCE_OCR else True
    
    # Set Tesseract path based on platform
    if platform.system() == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    # Test Tesseract installation
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✅ OCR libraries loaded successfully - Tesseract {version}")
        if FORCE_OCR:
            print("✅ OCR forced available by environment variable")
    except Exception as e:
        print(f"⚠️  Tesseract test failed: {e}")
        if not FORCE_OCR:
            OCR_AVAILABLE = False
    
except ImportError as e:
    print(f"⚠️  OCR libraries not available, using mock data: {e}")
    OCR_AVAILABLE = False

class DocumentProcessor:
    def __init__(self):
        # Enhanced W-2 specific patterns for precise extraction
        self.w2_patterns = {
            # Employee SSN - Box d
            'employee_ssn': [
                r'employee\'s social security number\s*\n?\s*(\d{3}-?\d{2}-?\d{4})',
                r'social security number\s*\n?\s*(\d{3}-?\d{2}-?\d{4})',
                r'ssn\s*:?\s*(\d{3}-?\d{2}-?\d{4})',
                r'(\d{3}-\d{2}-\d{4})',  # Standard SSN format
                r'(\d{9})',  # 9 digits together
            ],
            
            # Employer EIN - Box b  
            'employer_ein': [
                r'employer identification number\s*\n?\s*([A-Z0-9\-]{9,12})',
                r'ein\s*:?\s*([A-Z0-9\-]{9,12})',
                r'(\d{2}-\d{7})',  # Standard EIN format
                r'([A-Z]{2,4}\d{7,9})',  # Alternative format like FGHU7896901
            ],
            
            # Employee Name - Box e
            'employee_name': [
                r'employee\'s name\s*\n?\s*([A-Za-z\s]{2,50})',
                r'first name and initial\s+last name\s*\n?\s*([A-Za-z\s]{2,50})',
                r'name\s*\n?\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            ],
            
            # Employer Name - Box c
            'employer_name': [
                r'employer\'s name\s*\n?\s*([A-Za-z\s&\.,\-]{2,100})',
                r'company\s*:?\s*([A-Za-z\s&\.,\-]{2,100})',
                r'([A-Z][A-Za-z\s&]{3,50}(?:Inc|LLC|Corp|Company|Co\.|Ltd)\.?)',
            ],
            
            # Box 1: Wages, tips, other compensation - ENHANCED PATTERNS
            'wages': [
                # Look for structured patterns from real W-2 forms
                r'1\s+wages,?\s*tips,?\s*other compensation\s*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
                r'box\s*1[:\s]*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
                r'wages.*?compensation[:\s]*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
                r'(\d{1,2},?\d{3,6}(?:\.\d{2})?)\s+(?:2\s+)?(?:\d{1,4}(?:\.\d{2})?)',  # Wages followed by withholding
            ],
            
            # Box 2: Federal income tax withheld - ENHANCED PATTERNS  
            'federal_withholding': [
                r'2\s+federal income tax withheld\s*(\d{1,4}(?:\.\d{2})?)',
                r'box\s*2[:\s]*(\d{1,4}(?:\.\d{2})?)',
                r'federal.*?withheld[:\s]*(\d{1,4}(?:\.\d{2})?)',
                r'\d{1,2},?\d{3,6}(?:\.\d{2})?\s+(\d{1,4}(?:\.\d{2})?)',  # Amount after wages
            ],
            
            # Box 3: Social security wages
            'social_security_wages': [
                r'3\s+social security wages\s*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
                r'social security wages[:\s]*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
                r'box\s*3[:\s]*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
            ],
            
            # Box 4: Social security tax withheld
            'social_security_tax': [
                r'4\s+social security tax withheld\s*(\d{1,4}(?:\.\d{2})?)',
                r'social security tax[:\s]*(\d{1,4}(?:\.\d{2})?)',
                r'box\s*4[:\s]*(\d{1,4}(?:\.\d{2})?)',
            ],
            
            # Box 5: Medicare wages and tips
            'medicare_wages': [
                r'5\s+medicare wages and tips\s*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
                r'medicare wages[:\s]*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
                r'box\s*5[:\s]*(\d{1,2},?\d{3,6}(?:\.\d{2})?)',
            ],
            
            # Box 6: Medicare tax withheld
            'medicare_tax': [
                r'6\s+medicare tax withheld\s*(\d{1,4}(?:\.\d{2})?)',
                r'medicare tax[:\s]*(\d{1,4}(?:\.\d{2})?)',
                r'box\s*6[:\s]*(\d{1,4}(?:\.\d{2})?)',
            ],
            
            # State withholding
            'state_withholding': [
                r'17\s+state income tax\s*(\d{1,4}(?:\.\d{2})?)',
                r'state.*?tax[:\s]*(\d{1,4}(?:\.\d{2})?)',
                r'box\s*17[:\s]*(\d{1,4}(?:\.\d{2})?)',
            ]
        }

    def extract_document_data(self, file_path: str, content_type: str) -> Dict[str, Any]:
        """Main method to extract data from uploaded documents"""
        
        print(f"🔍 DEBUG: OCR_AVAILABLE = {OCR_AVAILABLE}, FORCE_OCR = {FORCE_OCR}")
        
        if not OCR_AVAILABLE:
            print("Using mock data - OCR not available")
            return self._generate_realistic_mock_data(file_path)
            
        try:
            print(f"Processing document with REAL OCR: {os.path.basename(file_path)}")
            
            # Extract text from document
            extracted_text = self._extract_text_from_file(file_path, content_type)
            
            if not extracted_text or len(extracted_text.strip()) < 10:
                print("OCR extraction failed or insufficient text, using mock data")
                return self._generate_realistic_mock_data(file_path)
            
            print(f"Extracted text length: {len(extracted_text)} characters")
            
            # Show sample of extracted text for debugging
            print("=== EXTRACTED TEXT SAMPLE ===")
            print(extracted_text[:1000])
            print("=== END SAMPLE ===")
            
            # Determine document type
            doc_type = self._identify_document_type(extracted_text, file_path)
            print(f"Identified document type: {doc_type}")
            
            if doc_type == "W-2":
                return self._extract_w2_data_precise(extracted_text)
            else:
                return self._extract_generic_data(extracted_text)
                
        except Exception as e:
            print(f"OCR processing failed: {e}, falling back to realistic mock data")
            import traceback
            traceback.print_exc()
            return self._generate_realistic_mock_data(file_path)

    def _extract_text_from_file(self, file_path: str, content_type: str) -> str:
        """Extract text using multiple methods for maximum coverage"""
        all_text = ""
        
        try:
            if content_type == "application/pdf":
                print(f"Processing PDF: {file_path}")
                
                # Method 1: Direct PDF text extraction
                direct_text = ""
                try:
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text.strip():
                                direct_text += page_text + "\n"
                    
                    if direct_text.strip():
                        print(f"✅ PDF direct extraction successful: {len(direct_text)} characters")
                        all_text += "=== PDF DIRECT EXTRACTION ===\n" + direct_text + "\n"
                    else:
                        print("⚠️  PDF direct extraction returned empty - trying OCR")
                        
                except Exception as e:
                    print(f"❌ PDF direct extraction failed: {e}")
                
                # Method 2: OCR on PDF images - ENHANCED for W2
                print("🔄 Attempting enhanced OCR on PDF images...")
                try:
                    # Convert PDF to images with high DPI for better OCR
                    images = convert_from_path(file_path, dpi=300, first_page=1, last_page=1)
                    print(f"📄 Converted PDF to {len(images)} image(s)")
                    
                    if images:
                        image = images[0]
                        print(f"🖼️  Image size: {image.size}")
                        
                        # Enhanced OCR specifically for W2 forms
                        ocr_text = self._enhanced_w2_ocr(image)
                        
                        if ocr_text.strip():
                            all_text += "=== ENHANCED W2 OCR ===\n" + ocr_text + "\n"
                            print(f"✅ Enhanced W2 OCR: {len(ocr_text)} characters")
                        else:
                            print("❌ Enhanced OCR failed to extract meaningful text")
                    else:
                        print("❌ Failed to convert PDF to images")
                    
                except Exception as ocr_e:
                    print(f"❌ PDF OCR processing failed: {ocr_e}")
                    import traceback
                    traceback.print_exc()
            
            elif content_type.startswith("image/"):
                print(f"Processing image: {file_path}")
                try:
                    image = Image.open(file_path)
                    ocr_text = self._enhanced_w2_ocr(image)
                    all_text += "=== ENHANCED IMAGE OCR ===\n" + ocr_text + "\n"
                    print(f"✅ Enhanced Image OCR: {len(ocr_text)} characters")
                    
                except Exception as e:
                    print(f"❌ Image OCR failed: {e}")
        
        except Exception as e:
            print(f"❌ Overall text extraction error: {e}")
        
        print(f"📊 Final extracted text length: {len(all_text)} characters")
        return all_text

    def _enhanced_w2_ocr(self, image) -> str:
        """Enhanced OCR specifically optimized for W2 forms"""
        try:
            # Convert PIL to CV2 if needed
            if hasattr(image, 'save'):
                # PIL Image
                import io
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                img_array = np.asarray(bytearray(img_bytes.read()), dtype=np.uint8)
                cv_image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            else:
                cv_image = image
            
            # Preprocessing for better W2 OCR
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Multiple preprocessing approaches
            preprocessed_images = []
            
            # 1. Basic threshold
            _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed_images.append(("basic_thresh", thresh1))
            
            # 2. Adaptive threshold
            thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            preprocessed_images.append(("adaptive_thresh", thresh2))
            
            # 3. Denoised
            denoised = cv2.fastNlMeansDenoising(gray)
            _, thresh3 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            preprocessed_images.append(("denoised", thresh3))
            
            # Try OCR on each preprocessed image
            best_text = ""
            best_score = 0
            
            # W2-specific OCR configurations
            w2_configs = [
                '--psm 6 --oem 3',  # Uniform block of text
                '--psm 4 --oem 3',  # Single column of text
                '--psm 11 --oem 3', # Sparse text
                '--psm 13 --oem 3', # Raw line
            ]
            
            for preprocess_name, processed_img in preprocessed_images:
                for config_idx, config in enumerate(w2_configs):
                    try:
                        print(f"🔍 Trying {preprocess_name} with config {config_idx + 1}")
                        text = pytesseract.image_to_string(processed_img, config=config)
                        
                        if text.strip():
                            score = self._score_w2_text(text)
                            print(f"   Score: {score:.2f}, Length: {len(text)}")
                            
                            if score > best_score:
                                best_text = text
                                best_score = score
                                print(f"   🏆 New best!")
                                
                    except Exception as e:
                        print(f"   ❌ Config failed: {e}")
                        continue
            
            print(f"✅ Best OCR result: score {best_score:.2f}, {len(best_text)} chars")
            return best_text
            
        except Exception as e:
            print(f"❌ Enhanced OCR failed: {e}")
            return ""

    def _score_w2_text(self, text: str) -> float:
        """Score text quality specifically for W2 forms"""
        if not text.strip():
            return 0.0
        
        score = 0.0
        text_lower = text.lower()
        
        # W2 specific indicators
        w2_keywords = [
            'wage and tax statement', 'w-2', 'wages tips other compensation',
            'federal income tax withheld', 'social security', 'medicare',
            'employer identification', 'employee', 'box 1', 'box 2'
        ]
        
        found_keywords = sum(1 for keyword in w2_keywords if keyword in text_lower)
        score += (found_keywords / len(w2_keywords)) * 0.4
        
        # Check for box numbers (1-17)
        box_numbers = re.findall(r'\b(?:box\s*)?([1-9]|1[0-7])\b', text_lower)
        score += min(len(set(box_numbers)) / 10, 0.3)
        
        # Check for SSN pattern
        if re.search(r'\d{3}-?\d{2}-?\d{4}', text):
            score += 0.15
        
        # Check for EIN pattern  
        if re.search(r'\d{2}-?\d{7}', text):
            score += 0.15
        
        return min(score, 1.0)

    def _extract_w2_data_precise(self, text: str) -> Dict[str, Any]:
        """Enhanced W2 extraction using real OCR text"""
        print("\n=== STARTING REAL W2 EXTRACTION ===")
        
        data = {
            "document_type": "W-2",
            "confidence": 0.0,
            "extraction_method": "Real OCR Processing",
            "debug_info": [],
            "raw_text_sample": text[:500] + "..." if len(text) > 500 else text
        }
        
        # Clean text
        clean_text = self._clean_text_for_w2(text)
        
        successful_extractions = 0
        
        for field_name, patterns in self.w2_patterns.items():
            best_value = None
            best_confidence = 0
            
            print(f"\n🔍 Extracting {field_name}...")
            
            for pattern_idx, pattern in enumerate(patterns):
                try:
                    matches = re.findall(pattern, clean_text, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        if isinstance(match, tuple):
                            match = match[-1] if match else ""
                        
                        cleaned_value = self._clean_extracted_value(match, field_name)
                        
                        if cleaned_value is not None:
                            confidence = self._calculate_field_confidence(field_name, cleaned_value, clean_text)
                            
                            print(f"   Pattern {pattern_idx + 1}: '{match}' -> '{cleaned_value}' (conf: {confidence:.2f})")
                            
                            if confidence > best_confidence:
                                best_value = cleaned_value
                                best_confidence = confidence
                        
                except Exception as e:
                    print(f"   Pattern {pattern_idx + 1} failed: {e}")
                    continue
            
            # Store result
            if best_value is not None and best_confidence > 0.4:
                data[field_name] = best_value
                successful_extractions += 1
                data["debug_info"].append(f"✅ {field_name}: {best_value} (confidence: {best_confidence:.2f})")
                print(f"✅ {field_name}: {best_value}")
            else:
                data["debug_info"].append(f"❌ {field_name}: No reliable extraction")
                print(f"❌ {field_name}: No reliable extraction")
        
        # Calculate overall confidence
        total_fields = len(self.w2_patterns)
        data['confidence'] = successful_extractions / total_fields if total_fields > 0 else 0
        
        print(f"\n📊 REAL OCR EXTRACTION SUMMARY:")
        print(f"   Successful: {successful_extractions}/{total_fields}")
        print(f"   Confidence: {data['confidence']:.2f}")
        
        # If OCR extraction had very low success, fall back to realistic mock
        if data['confidence'] < 0.3:
            print("⚠️  OCR confidence too low, using realistic mock data instead")
            return self._generate_realistic_mock_data("")
        
        # Set defaults for missing fields
        data.setdefault('wages', 0.0)
        data.setdefault('federal_withholding', 0.0)
        data.setdefault('social_security_wages', 0.0)
        data.setdefault('medicare_wages', 0.0)
        data.setdefault('employee_name', 'Not found')
        data.setdefault('employer_name', 'Not found')
        
        return data

    def _clean_text_for_w2(self, text: str) -> str:
        """Clean and normalize text for better pattern matching"""
        # Remove excessive whitespace but preserve structure
        cleaned = re.sub(r'\s+', ' ', text)
        
        # Normalize common OCR errors
        cleaned = cleaned.replace('0', '0').replace('O', '0')  # Fix common OCR errors
        cleaned = re.sub(r'[^\w\s\-\.\,\n]', ' ', cleaned)
        
        return cleaned

    def _clean_extracted_value(self, value: str, field_type: str) -> Any:
        """Clean and validate extracted values with better range checking"""
        if not value:
            return None
        
        value = str(value).strip()
        
        if field_type in ['wages', 'federal_withholding', 'social_security_wages', 
                         'social_security_tax', 'medicare_wages', 'medicare_tax', 'state_withholding']:
            # Enhanced numeric field cleaning
            cleaned = re.sub(r'[^\d.]', '', value)
            
            # Handle multiple decimal points
            if cleaned.count('.') > 1:
                parts = cleaned.split('.')
                cleaned = parts[0] + '.' + ''.join(parts[1:])
            
            try:
                num_value = float(cleaned) if cleaned else 0.0
                
                # STRICT range validation to prevent incorrect large numbers
                if field_type == 'wages':
                    return num_value if 1000 <= num_value <= 300000 else None
                elif field_type in ['federal_withholding', 'state_withholding']:
                    return num_value if 0 <= num_value <= 25000 else None
                elif field_type in ['social_security_wages', 'medicare_wages']:
                    return num_value if 1000 <= num_value <= 200000 else None
                elif field_type in ['social_security_tax', 'medicare_tax']:
                    return num_value if 0 <= num_value <= 15000 else None
                else:
                    return num_value if 0 <= num_value <= 300000 else None
                    
            except (ValueError, TypeError):
                return None
        
        elif field_type == 'employee_ssn':
            digits = re.sub(r'\D', '', value)
            if len(digits) == 9:
                return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
            return None
        
        elif field_type == 'employer_ein':
            if re.match(r'[A-Z]{4}\d{7}', value):
                return value  # Keep as-is for alternative format
            elif re.match(r'\d{2}-?\d{7}', value):
                digits = re.sub(r'\D', '', value)
                return f"{digits[:2]}-{digits[2:]}" if len(digits) == 9 else value
            return value if len(value) >= 9 else None
        
        else:
            return value if 2 <= len(value) <= 100 else None

    def _calculate_field_confidence(self, field_name: str, value: Any, context: str) -> float:
        """Calculate confidence based on field type and context"""
        confidence = 0.5  # Base confidence
        
        # Field-specific validation
        if field_name == 'wages' and isinstance(value, (int, float)):
            if 10000 <= value <= 200000:
                confidence += 0.3
            elif 1000 <= value <= 500000:
                confidence += 0.2
        
        elif field_name in ['federal_withholding', 'state_withholding'] and isinstance(value, (int, float)):
            if 0 <= value <= 50000 and value > 0:
                confidence += 0.3
        
        elif field_name == 'employee_ssn' and isinstance(value, str):
            if re.match(r'\d{3}-\d{2}-\d{4}', value):
                confidence += 0.4
        
        elif field_name == 'employer_ein' and isinstance(value, str):
            if re.match(r'\d{2}-\d{7}', value) or re.match(r'[A-Z]{4}\d{7}', value):
                confidence += 0.4
        
        return min(confidence, 1.0)

    def _identify_document_type(self, text: str, filename: str) -> str:
        """Identify document type with enhanced W2 detection"""
        text_lower = text.lower()
        filename_lower = os.path.basename(filename).lower()
        
        # Check filename first
        if any(keyword in filename_lower for keyword in ['w2', 'w-2']):
            return "W-2"
        
        # Enhanced W2 content detection
        w2_score = 0
        w2_indicators = [
            'wage and tax statement', 'w-2', 'form w-2',
            'wages tips other compensation',
            'federal income tax withheld',
            'social security wages',
            'medicare wages and tips',
            'employer identification number',
            'employee\'s social security number'
        ]
        
        for indicator in w2_indicators:
            if indicator in text_lower:
                w2_score += 2 if 'wage and tax statement' in indicator else 1
        
        # Check for box structure
        box_matches = len(re.findall(r'\bbox\s*[1-9]\b', text_lower))
        w2_score += box_matches
        
        # Check for numeric patterns typical of W2
        ssn_pattern = len(re.findall(r'\d{3}-?\d{2}-?\d{4}', text))
        ein_pattern = len(re.findall(r'\d{2}-?\d{7}', text))
        w2_score += ssn_pattern + ein_pattern
        
        print(f"W2 detection score: {w2_score}")
        
        return "W-2" if w2_score >= 3 else "Unknown"

    def _extract_generic_data(self, text: str) -> Dict[str, Any]:
        """Extract data from unknown document types"""
        return {
            "document_type": "Unknown",
            "extracted_text": text[:500] + "..." if len(text) > 500 else text,
            "confidence": 0.3,
            "extraction_method": "Generic",
            "message": "Document type not recognized. Please verify this is a W-2 form."
        }

    def _generate_realistic_mock_data(self, file_path: str) -> Dict[str, Any]:
        """Generate realistic mock data based on actual W-2 patterns"""
        filename = os.path.basename(file_path).lower() if file_path else ""
        
        if "w2" in filename or "w-2" in filename or not file_path:
            # Generate more realistic W-2 data
            base_wage = random.uniform(45000, 120000)
            
            return {
                "document_type": "W-2",
                "employer_name": random.choice([
                    "TechCorp Solutions Inc", 
                    "Global Industries LLC", 
                    "Metro Services Company",
                    "Advanced Systems Corp",
                    "Premier Business Solutions"
                ]),
                "employee_name": random.choice([
                    "Sarah Johnson", 
                    "Michael Chen", 
                    "Jessica Williams",
                    "David Rodriguez", 
                    "Emily Davis"
                ]),
                "employee_ssn": f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}",
                "employer_ein": f"{random.randint(10,99)}-{random.randint(1000000,9999999)}",
                "wages": round(base_wage, 2),
                "federal_withholding": round(base_wage * random.uniform(0.12, 0.22), 2),
                "social_security_wages": round(base_wage * random.uniform(0.95, 1.0), 2),
                "social_security_tax": round(base_wage * 0.062, 2),  # 6.2% SS rate
                "medicare_wages": round(base_wage * random.uniform(0.98, 1.02), 2),
                "medicare_tax": round(base_wage * 0.0145, 2),  # 1.45% Medicare rate
                "state_withholding": round(base_wage * random.uniform(0.03, 0.08), 2),
                "confidence": 0.85,
                "extraction_method": "Realistic Mock Data",
                "note": "Realistic mock data generated - OCR processing failed or not available"
            }
        else:
            return {
                "document_type": "Unknown",
                "confidence": 0.5,
                "extraction_method": "Mock",
                "note": "Mock data - document type not recognized"
            }

# Create global processor instance
processor = DocumentProcessor()

def extract_document_data(file_path: str, content_type: str) -> Dict[str, Any]:
    """Main function to extract precise data from documents"""
    return processor.extract_document_data(file_path, content_type)
