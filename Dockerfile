FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install PyTorch CPU-only wheels
RUN pip install --no-cache-dir torch==2.3.1 torchvision==0.18.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu

# Install core dependencies
RUN pip install --no-cache-dir numpy==1.26.4
RUN pip install --no-cache-dir scipy==1.9.3

# Install audio libraries
RUN pip install --no-cache-dir librosa==0.10.2.post1 soundfile==0.12.1 mido==1.3.2

# Install Demucs
RUN pip install --no-cache-dir demucs==4.0.0

# Install Basic Pitch with TensorFlow support (pinned)
RUN pip install --no-cache-dir "basic-pitch[tf]==0.3.0"
# Optional tool: YouTube download helper
RUN pip install --no-cache-dir yt-dlp

# Set working directory
WORKDIR /work

# Copy the pipeline script
COPY pipeline.py /usr/local/bin/pipeline.py
RUN chmod +x /usr/local/bin/pipeline.py

# Set default command to run the pipeline (can override with docker run ...)
ENTRYPOINT ["python", "/usr/local/bin/pipeline.py"]
