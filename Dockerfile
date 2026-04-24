#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2014-2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#

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

