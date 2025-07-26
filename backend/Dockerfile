FROM python:3.10-slim

# Install system dependencies for OCR and document processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libxrandr2 \
    libasound2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Fix Tesseract language data path issues
RUN mkdir -p /usr/share/tesseract-ocr/4.00/tessdata/ && \
    mkdir -p /usr/share/tessdata/ && \
    find /usr -name "*.traineddata" -exec cp {} /usr/share/tesseract-ocr/4.00/tessdata/ \; && \
    find /usr -name "*.traineddata" -exec cp {} /usr/share/tessdata/ \; && \
    ls -la /usr/share/tesseract-ocr/4.00/tessdata/ && \
    ls -la /usr/share/tessdata/

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads
RUN chmod 755 uploads

# Set environment variables for better OCR performance and fix tessdata path
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Verify Tesseract installation and language data
RUN tesseract --version && \
    tesseract --list-langs && \
    echo "TESSDATA_PREFIX: $TESSDATA_PREFIX" && \
    ls -la $TESSDATA_PREFIX

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
