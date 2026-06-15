FROM python:3.10-slim-bookworm

# System dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install git+https://github.com/openai/whisper.git
RUN pip install -r requirements.txt --no-build-isolation

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/meetings data/transcripts data/outputs

# HF Spaces runs as non-root user - fix permissions
RUN chmod -R 777 data/

# HF Spaces expects the app on port 7860
EXPOSE 7860

# On HF Spaces we run both FastAPI + Gradio via this script
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 & python gradio_ui.py"]