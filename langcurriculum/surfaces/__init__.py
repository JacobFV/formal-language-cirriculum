"""Surfaces: the media an episode's text can be carried in.

Every surface here is a **transcode**. It takes the string the text surface
produced and re-presents it — as pixels, as words read aloud, as frames — without
changing the problem underneath. A picture is a picture *of the sentence*, not a
picture of the scene the sentence describes.

That restriction is the measurement, not a limitation. Because the surface is
provably incidental, a system that answers correctly through one and not another
has learned the surface. A native rendering would measure something else, and is
a later phase; renderers register against roles here so that adding one does not
disturb what exists. See ``INTENT.md``.

===========  ===========================================================
``text``     the string itself
``raster``   an 8-bit greyscale PNG, drawn with a bundled 5x7 font
``spoken``   the transcript a dictation would be read from
``video``    a sequence of PNG frames revealing the text over time
===========  ===========================================================

Each declares a ``RENDERER_VERSION``. It belongs in the address of any cached
rendering, because a renderer that changes without its version changing is how a
published corpus silently stops matching the code that made it.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .content import Asset, Content, Fidelity
from . import raster as _raster
from . import spoken as _spoken
from . import video as _video

__all__ = ["Asset", "Content", "Fidelity", "SURFACES", "RENDERER_VERSIONS",
           "transcode", "surface_names", "reproducibility"]

RENDERER_VERSION = "text_v1"


def _text_transcode(text: str, target: str = "", **_options) -> Content:
    """The identity surface. Kept explicit so ``text`` is not a special case."""
    return Content(surface="text", text=text, target=target,
                   meta={"renderer": RENDERER_VERSION})


#: surface name -> the function that renders text into it
SURFACES: dict[str, Callable[..., Content]] = {
    "text": _text_transcode,
    "raster": _raster.transcode,
    "spoken": _spoken.transcode,
    "video": _video.transcode,
}

#: surface name -> the version of the renderer behind it
RENDERER_VERSIONS: dict[str, str] = {
    "text": RENDERER_VERSION,
    "raster": _raster.RENDERER_VERSION,
    "spoken": _spoken.RENDERER_VERSION,
    "video": _video.RENDERER_VERSION,
}

#: What "the same bytes" actually means, per surface, stated at the granularity
#: it holds. Quoted by the CLI and the site rather than a blanket claim.
REPRODUCIBILITY: dict[str, str] = {
    "text": "exact, given the language database version",
    "raster": "exact, given the renderer version and the bundled font",
    "spoken": "exact; the transcript is rule-based and the audio step is pinned "
              "separately",
    "video": "exact for the frames; containers are packaging and are not hashed",
}


def surface_names() -> list[str]:
    return list(SURFACES)


def reproducibility(surface: str) -> str:
    return REPRODUCIBILITY.get(surface, "unstated")


def transcode(text: str, surface: str = "text", *, target: str = "",
              choices: Iterable[str] = (), **options: Any) -> Content:
    """Render text into a surface.

    ``choices`` is passed through for the surfaces that need the answer set to
    say whether the episode survived the transcode — dictation is the one that
    does, because two options can sound the same.
    """
    if surface not in SURFACES:
        raise ValueError(f"unknown surface {surface!r}; try one of {surface_names()}")
    return SURFACES[surface](text, target, choices=tuple(choices), **options) \
        if surface == "spoken" else SURFACES[surface](text, target, **options)


def transcode_example(example, surface: str = "text", **options: Any) -> Content:
    """Render an :class:`~langcurriculum.lesson.Example` into a surface."""
    return transcode(example.prompt, surface, target=example.target,
                     choices=example.choices, **options)
