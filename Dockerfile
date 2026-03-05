# Containerfile for PySceneDetect
# Copyright (C) 2026 FNGarvin. All rights reserved.
# License: BSD-3-Clause

FROM python:3.11.11-slim

# Create a non-root user for security hardening
RUN useradd -m scenedetect

# Set working directory and copy files with correct ownership
WORKDIR /app
COPY --chown=scenedetect:scenedetect . .

# Install necessary system dependencies as root first
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    mkvtoolnix && \
    rm -rf /var/lib/apt/lists/*

# Install PySceneDetect with headless OpenCV and other optional media backends
# pyav is highly recommended for faster/more robust video decodes
# moviepy provides an alternative video splitting backend
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install ".[opencv-headless,pyav,moviepy]"

# Switch to the non-root user
USER scenedetect

# The default behavior is to run the CLI
ENTRYPOINT ["scenedetect"]

# EOF Dockerfile
