FROM python:3.10-slim

# Install system dependencies for OCR and document processing
RUN apt-get update && apt-get install -y \
    # Core OCR dependencies
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-osd \
    libtesseract-dev \
    # PDF processing
    poppler-utils \
    # Image processing
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libxrandr2 \
    libasound2 \
    # Utilities
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for OCR
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV FORCE_OCR_AVAILABLE=true

# Create tessdata directory and ensure it has proper language files
RUN mkdir -p /usr/share/tesseract-ocr/4.00/tessdata && \
    mkdir -p /usr/share/tessdata && \
    # Find and copy all traineddata files to both locations
    find /usr -name "*.traineddata" -exec cp {} /usr/share/tesseract-ocr/4.00/tessdata/ \; 2>/dev/null || true && \
    find /usr -name "*.traineddata" -exec cp {} /usr/share/tessdata/ \; 2>/dev/null || true && \
    # Download essential traineddata files if missing
    cd /usr/share/tesseract-ocr/4.00/tessdata && \
    test -f eng.traineddata || wget -q https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata && \
    test -f osd.traineddata || wget -q https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata && \
    # Copy to backup location
    cp *.traineddata /usr/share/tessdata/ 2>/dev/null || true

# Verify Tesseract installation and show debugging info
RUN echo "=== TESSERACT INSTALLATION VERIFICATION ===" && \
    tesseract --version && \
    echo "=== AVAILABLE LANGUAGES ===" && \
    tesseract --list-langs && \
    echo "=== TESSDATA LOCATIONS ===" && \
    echo "TESSDATA_PREFIX: $TESSDATA_PREFIX" && \
    ls -la $TESSDATA_PREFIX/ || echo "Primary tessdata location not found" && \
    ls -la /usr/share/tessdata/ || echo "Backup tessdata location not found" && \
    echo "=== TESSERACT EXECUTABLE LOCATION ===" && \
    which tesseract && \
    echo "=== TESSERACT SIMPLE TEST ===" && \
    echo "hello" | tesseract stdin stdout --psm 8 && \
    echo "=== INSTALLATION VERIFICATION COMPLETE ==="

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads && chmod 755 uploads

# Final OCR functionality test
RUN echo "=== FINAL OCR TEST ===" && \
    python -c "
import sys
import os
print('Testing OCR imports...')

try:
    import pytesseract
    print('✅ pytesseract imported successfully')
    
    from PIL import Image
    print('✅ PIL imported successfully')
    
    import PyPDF2
    print('✅ PyPDF2 imported successfully')
    
    from pdf2image import convert_from_path
    print('✅ pdf2image imported successfully')
    
    import cv2
    print('✅ cv2 imported successfully')
    
    import numpy as np
    print('✅ numpy imported successfully')
    
    # Test tesseract version
    version = pytesseract.get_tesseract_version()
    print(f'✅ Tesseract version: {version}')
    
    # Test language detection
    langs = pytesseract.get_languages()
    print(f'✅ Available languages: {langs}')
    
    # Test environment variables
    print(f'✅ TESSDATA_PREFIX: {os.environ.get(\"TESSDATA_PREFIX\", \"NOT SET\")}')
    print(f'✅ FORCE_OCR_AVAILABLE: {os.environ.get(\"FORCE_OCR_AVAILABLE\", \"NOT SET\")}')
    
    print('✅ ALL OCR TESTS PASSED - OCR SHOULD BE FULLY FUNCTIONAL')
    
except Exception as e:
    print(f'❌ OCR test failed: {e}')
    sys.exit(1)
" && echo "=== OCR SETUP COMPLETE ==="

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
