FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ffmpeg \
    nodejs \
    npm \
    git \
    curl \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel

# ── Install CPU-only torch first (prevents pip pulling 2GB CUDA wheel) ──
RUN pip install torch==2.2.2+cpu --index-url https://download.pytorch.org/whl/cpu

# ── Whisper (torch must already be installed before this) ──
RUN pip install \
    git+https://github.com/openai/whisper.git@04f449b8a437f1bbd3dba5c9f826aca972e7709a \
    --no-build-isolation

# ── Everything else (torch already satisfied, won't be re-downloaded) ──
RUN pip install -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --no-build-isolation

COPY . .

RUN mkdir -p data/meetings data/transcripts data/outputs

RUN chmod -R 777 data/

EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 & python gradio_ui.py"]