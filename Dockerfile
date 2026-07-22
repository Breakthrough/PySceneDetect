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

# Install the scenedetect-headless variant: full program (CLI + opencv-python-headless)
# with the optional media backends. The repo root pyproject builds scenedetect-core
# (library only, no CLI), so swap in the headless variant pyproject first.
# pyav is highly recommended for faster/more robust video decodes
# moviepy provides an alternative video splitting backend
RUN --mount=type=cache,target=/root/.cache/pip \
    cp packaging/variants/pyproject-scenedetect-headless.toml pyproject.toml && \
    pip install ".[pyav,moviepy]" && \
    # TODO(https://github.com/Zulko/moviepy/issues/2553): moviepy caps pillow<12.0, but 11.x has
    # CVEs only fixed in 12.3.0+. Tests pass against 12.3.0; drop this once moviepy lifts the cap.
    pip install "pillow==12.3.0"

# Switch to the non-root user
USER scenedetect

# The default behavior is to run the CLI
ENTRYPOINT ["scenedetect"]

