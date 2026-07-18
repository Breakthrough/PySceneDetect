#
#            PySceneDetect: Python-Based Video Scene Detector
#   -------------------------------------------------------------------
#     [  Site:    https://scenedetect.com                           ]
#     [  Docs:    https://scenedetect.com/docs/                     ]
#     [  Github:  https://github.com/Breakthrough/PySceneDetect/    ]
#
# Copyright (C) 2026 Brandon Castellano <http://www.bcastell.com>.
# PySceneDetect is licensed under the BSD 3-Clause License; see the
# included LICENSE file, or visit one of the above pages for details.
#
"""Tee one VideoStream into N consumer streams sharing a single decode.

Used by the benchmark sweep harness to amortize video decoding across multiple detector
configurations running in parallel: one source decode feeds N consumer streams, each
read by an independent detection thread. The source is paced by the slowest consumer
(blocking ``put`` into bounded per-consumer queues), so peak memory is bounded by
``n * prefetch`` frames.

Internal API (underscore-prefixed module). Not part of the public surface.
"""

from __future__ import annotations

import contextlib
import queue
import threading
from fractions import Fraction

import numpy as np

from scenedetect.common import FrameTimecode, TimecodeLike
from scenedetect.video_stream import SeekError, VideoStream

_EOF = object()
"""Sentinel placed on each consumer queue when the source reaches end-of-stream."""


class FanOutVideoStream:
    """Drives one source :class:`VideoStream` and fans frames out to N consumer streams.

    Usage::

        source = open_video("video.mp4")
        fan = FanOutVideoStream(source, n=4)
        fan.start()
        try:
            for i in range(4):
                threading.Thread(target=worker, args=(fan.stream(i),)).start()
            # ... join workers ...
        finally:
            fan.close()

    The wrapper owns one background reader thread. Each ``stream(i)`` handle is a
    forward-only :class:`VideoStream` that reads from its own queue. ``seek``/``reset``
    on a consumer raise :class:`SeekError` -- to re-run a sweep over the same source,
    call ``source.reset()`` on the underlying stream and build a fresh
    ``FanOutVideoStream`` for the next chunk.
    """

    def __init__(self, source: VideoStream, n: int, prefetch: int = 4):
        """
        Arguments:
            source: Already-opened ``VideoStream`` to read from.
            n: Number of consumer streams to expose. Must be >= 1.
            prefetch: Per-consumer queue depth. ``0`` is rendezvous (every frame waits
                for every consumer to take it); 4-8 absorbs jitter between consumers
                at the cost of up to ``n * prefetch`` resident frames.
        """
        if n < 1:
            raise ValueError("n must be at least 1")
        if prefetch < 0:
            raise ValueError("prefetch must be >= 0")
        self._source = source
        # queue.Queue(maxsize=0) means unbounded, which would defeat back-pressure.
        # prefetch=0 therefore maps to a 1-deep buffer (shallow, not strict rendezvous).
        qsize = prefetch if prefetch > 0 else 1
        self._queues: list[queue.Queue] = [queue.Queue(maxsize=qsize) for _ in range(n)]
        self._consumers: list[_FanOutConsumer] = [_FanOutConsumer(self, i) for i in range(n)]
        self._stop = threading.Event()
        self._reader: threading.Thread | None = None
        self._started = False
        self._closed = False
        self._reader_exc: BaseException | None = None

    @property
    def num_consumers(self) -> int:
        """Number of consumer streams exposed by this wrapper."""
        return len(self._consumers)

    def stream(self, i: int) -> VideoStream:
        """Return the i-th consumer ``VideoStream``."""
        return self._consumers[i]

    def start(self) -> None:
        """Spawn the reader thread. Idempotent; subsequent calls are no-ops."""
        if self._started:
            return
        self._started = True
        self._reader = threading.Thread(
            target=self._read_loop, name="FanOutVideoStream-reader", daemon=True
        )
        self._reader.start()

    def abort(self) -> None:
        """Signal the reader to stop. Called by consumers on EOF/error to unblock the source."""
        self._stop.set()
        # Drain queues so a put() blocked by maxsize wakes up.
        for q in self._queues:
            with contextlib.suppress(queue.Empty):
                while True:
                    q.get_nowait()

    def close(self) -> None:
        """Stop the reader thread and release resources. Idempotent."""
        if self._closed:
            return
        self._closed = True
        self.abort()
        if self._reader is not None:
            self._reader.join(timeout=5.0)

    def _read_loop(self) -> None:
        try:
            while not self._stop.is_set():
                frame = self._source.read()
                if frame is False:
                    break
                # Block per-consumer; slowest consumer paces the source.
                for q in self._queues:
                    while not self._stop.is_set():
                        try:
                            q.put(frame, timeout=0.1)
                            break
                        except queue.Full:
                            continue
                    if self._stop.is_set():
                        return
        except BaseException as e:
            self._reader_exc = e
        finally:
            # Sentinel must reach every consumer or its blocking read() deadlocks.
            # Drop the oldest frame whenever the queue is full; we are the sole writer,
            # so after a successful get_nowait() the queue has room for the EOF.
            for q in self._queues:
                while True:
                    try:
                        q.put_nowait(_EOF)
                        break
                    except queue.Full:
                        with contextlib.suppress(queue.Empty):
                            q.get_nowait()


class _FanOutConsumer(VideoStream):
    """One consumer-side handle exposed by :class:`FanOutVideoStream`.

    Forwards constant metadata (path, frame_rate, frame_size, etc.) to the source.
    Maintains its own ``frame_number`` / ``position`` -- both advance only when this
    consumer calls ``read()``, independent of the source's position or sibling
    consumers.
    """

    BACKEND_NAME = "fan_out"

    def __init__(self, parent: FanOutVideoStream, index: int):
        self._parent = parent
        self._index = index
        self._frame_number = 0
        self._eof = False

    @property
    def path(self) -> str:
        return self._parent._source.path

    @property
    def name(self) -> str:
        return self._parent._source.name

    @property
    def is_seekable(self) -> bool:
        return False

    @property
    def frame_rate(self) -> Fraction:
        return self._parent._source.frame_rate

    @property
    def duration(self) -> FrameTimecode | None:
        return self._parent._source.duration

    @property
    def frame_size(self) -> tuple[int, int]:
        return self._parent._source.frame_size

    @property
    def aspect_ratio(self) -> float:
        return self._parent._source.aspect_ratio

    @property
    def decode_failures(self) -> int:
        return self._parent._source.decode_failures

    @property
    def frame_number(self) -> int:
        return self._frame_number

    @property
    def position(self) -> FrameTimecode:
        # Mirrors VideoStream contract: "frame 1 corresponds to presentation time 0;
        # returns 0 even if frame_number is 1."
        n = max(0, self._frame_number - 1)
        return FrameTimecode(timecode=n, fps=self.frame_rate)

    @property
    def position_ms(self) -> float:
        if self._frame_number == 0:
            return 0.0
        fps = self.frame_rate
        return float(1000 * (self._frame_number - 1) * fps.denominator) / float(fps.numerator)

    def read(self, decode: bool = True) -> np.ndarray | bool:
        if self._eof:
            return False
        item = self._parent._queues[self._index].get()
        if item is _EOF:
            self._eof = True
            if self._parent._reader_exc is not None:
                raise self._parent._reader_exc
            return False
        self._frame_number += 1
        # The source already decoded the frame; decode=False just suppresses returning it.
        if not decode:
            return True
        return item  # type: ignore[return-value]

    def reset(self) -> None:
        raise SeekError("FanOutVideoStream consumers are forward-only; reset the source instead.")

    def seek(self, target: TimecodeLike) -> None:
        del target
        raise SeekError("FanOutVideoStream consumers are forward-only; seeking is not supported.")
