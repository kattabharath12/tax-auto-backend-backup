FROM python:3.10-slim

# Install system dependencies for OCR and document processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-osd \
    poppler-utils \
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
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Explicitly set Tesseract data directory and verify installation
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Download additional language data if needed
RUN mkdir -p /usr/share/tesseract-ocr/4.00/tessdata/ && \
    wget -O /usr/share/tesseract-ocr/4.00/tessdata/osd.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/osd.traineddata || true

# Verify Tesseract installation
RUN tesseract --version && \
    tesseract --list-langs && \
    ls -la /usr/share/tesseract-ocr/4.00/tessdata/

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads
RUN chmod 755 uploads

# Test OCR functionality during build
RUN python -c "
import sys
try:
    import pytesseract
    from PIL import Image
    import PyPDF2
    from pdf2image import convert_from_path
    import cv2
    import numpy as np
    print('✅ All OCR libraries imported successfully')
    
    # Test tesseract executable
    result = pytesseract.get_tesseract_version()
    print(f'✅ Tesseract version: {result}')
    
    # Set OCR_AVAILABLE to True in environment
    import os
    os.environ['FORCE_OCR_AVAILABLE'] = 'true'
    print('✅ OCR forced to available mode')
    
except Exception as e:
    print(f'❌ OCR setup failed: {e}')
    sys.exit(1)
"

# Set environment variable to force OCR availability
ENV FORCE_OCR_AVAILABLE=true

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
