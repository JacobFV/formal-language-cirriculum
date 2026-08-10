"""Text as a sequence of frames, so that reading it takes time.

A page can be taken in at a glance; a video cannot. Revealing the same text a
line at a time forces integration across frames, which is a real perceptual
demand and not one the raster surface makes — while still carrying exactly the
same string, so the task underneath is untouched.

What this produces is a **frame sequence**, and that is deliberate. Frames are
deterministic and hashable; a container is not. Codecs differ between builds, so
if the artifact were an ``.mp4`` the claim "same seed gives the same bytes" would
be false. Packaging frames into a container is a separate step, versioned
separately, and outside the reproducibility guarantee. See ``INTENT.md``.
"""

from __future__ import annotations

from typing import Sequence

from .content import Asset, Content, Fidelity
from .raster import coverage, layout, png, render

__all__ = ["RENDERER_VERSION", "frames", "transcode"]

RENDERER_VERSION = "video_v1"


def frames(text: str, *, mode: str = "reveal", window: int = 12,
           columns: int = 88, **options) -> list[bytes]:
    """The frames of a reading, as PNG bytes.

    ``reveal`` adds one line per frame, so the page fills up and the reader
    accumulates. ``scroll`` keeps a fixed window and moves it down, so nothing is
    on screen for the whole clip and the reader has to hold it.
    """
    lines = layout(text, columns=columns)
    opts = {k: v for k, v in options.items()
            if k in ("scale", "padding", "line_gap", "letter_gap", "invert")}
    out: list[bytes] = []
    if mode == "reveal":
        for i in range(1, len(lines) + 1):
            shown = lines[:i] + [""] * (len(lines) - i)          # keep the page size fixed
            frame = png(render("\n".join(shown), columns=columns, **opts))
            # Revealing a blank line changes nothing, and a frame identical to the
            # one before it is dead time rather than a reading step.
            if out and frame == out[-1]:
                continue
            out.append(frame)
    elif mode == "scroll":
        span = max(1, window)
        last = max(1, len(lines) - span + 1)
        for i in range(last):
            shown = lines[i:i + span]
            out.append(png(render("\n".join(shown), columns=columns, **opts)))
    else:
        raise ValueError(f"unknown mode {mode!r}; try reveal or scroll")
    return out


def transcode(text: str, target: str = "", **options) -> Content:
    """Render a prompt as a frame sequence."""
    missing = coverage(text)
    mode = options.get("mode", "reveal")
    data = frames(text, **options)
    notes = []
    if missing:
        notes.append(f"{len(missing)} characters outside the bundled font were "
                     f"drawn as a box")
    if mode == "scroll":
        notes.append("a scrolling window shows no frame containing the whole "
                     "episode; this is a working-memory demand the text surface "
                     "does not make")
    return Content(
        surface="video", text=text, target=target,
        assets=tuple(Asset(mime="image/png", data=d, role="frame", index=i)
                     for i, d in enumerate(data)),
        fidelity=Fidelity(lossless=not missing, dropped=missing, notes=tuple(notes)),
        meta={"renderer": RENDERER_VERSION, "mode": mode, "frames": len(data),
              "container": "none; frames are the artifact"})
