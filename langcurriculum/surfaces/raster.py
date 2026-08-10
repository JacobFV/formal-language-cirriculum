"""Text as pixels: a deterministic rasterizer with no dependencies.

Vector internally, raster at the boundary — the same arrangement as text, which
is symbolic internally and characters at the boundary. A glyph is a small grid,
a page is a layout over glyphs, and the last step turns that into a PNG. Nothing
is sampled, nothing is anti-aliased, no font is loaded from the host, so the
bytes are a function of the text and the options and nothing else.

The reproducibility claim is therefore "same text, same options, same
``RENDERER_VERSION`` gives the same bytes", which is what
:data:`RENDERER_VERSION` is for. Bumping it is how you say a rendering changed;
leaving it alone while changing the output is how a published corpus silently
stops matching the code that made it.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Sequence

from .content import Asset, Content, Fidelity
from .font import HEIGHT, WIDTH, covers, glyph

__all__ = ["RENDERER_VERSION", "Page", "render", "png", "coverage", "layout"]

#: Bump when a change would alter the bytes of an already-published rendering.
RENDERER_VERSION = "raster_v1"

_SIG = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class Page:
    """A rasterized page: width, height and one byte of grey per pixel."""

    width: int
    height: int
    pixels: bytes

    def ascii_art(self, on: str = "#", off: str = ".") -> str:
        """The page as text, for eyeballing a glyph without opening an image."""
        return "\n".join(
            "".join(on if self.pixels[y * self.width + x] < 128 else off
                    for x in range(self.width))
            for y in range(self.height))


def layout(text: str, *, columns: int = 88) -> list[str]:
    """Hard-wrap to a column count, preserving the paragraph structure.

    Wrapping is by character rather than by word measurement because the font is
    fixed-width: every glyph is exactly :data:`~langcurriculum.surfaces.font.WIDTH`
    wide, so a column count is a pixel count divided by a constant, and the two
    never disagree.
    """
    out: list[str] = []
    for raw in text.split("\n"):
        if not raw:
            out.append("")
            continue
        line = ""
        for word in raw.split(" "):
            while len(word) > columns:                 # a token longer than the page
                if line:
                    out.append(line)
                    line = ""
                out.append(word[:columns])
                word = word[columns:]
            if not line:
                line = word
            elif len(line) + 1 + len(word) <= columns:
                line = f"{line} {word}"
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def render(text: str, *, columns: int = 88, scale: int = 2, padding: int = 8,
           line_gap: int = 3, letter_gap: int = 1, invert: bool = False) -> Page:
    """Lay text out and draw it, one glyph at a time."""
    lines = layout(text, columns=columns)
    cell_w = WIDTH + letter_gap
    cell_h = HEIGHT + line_gap
    width = padding * 2 + cell_w * columns * scale
    height = padding * 2 + max(1, len(lines)) * cell_h * scale
    bg, fg = (0, 255) if invert else (255, 0)
    buf = bytearray([bg]) * (width * height)

    for row, line in enumerate(lines):
        for col, ch in enumerate(line[:columns]):
            bitmap = glyph(ch)
            ox = padding + col * cell_w * scale
            oy = padding + row * cell_h * scale
            for gy in range(HEIGHT):
                srow = bitmap[gy]
                for gx in range(WIDTH):
                    if srow[gx] != "#":
                        continue
                    for sy in range(scale):
                        y = oy + gy * scale + sy
                        base = y * width + ox + gx * scale
                        for sx in range(scale):
                            buf[base + sx] = fg
    return Page(width, height, bytes(buf))


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def png(page: Page) -> bytes:
    """An 8-bit greyscale PNG. No palette, no interlace, no ancillary chunks."""
    raw = bytearray()
    for y in range(page.height):
        raw.append(0)                                  # filter type 0: none
        raw += page.pixels[y * page.width:(y + 1) * page.width]
    ihdr = struct.pack(">IIBBBBB", page.width, page.height, 8, 0, 0, 0, 0)
    return (_SIG + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + _chunk(b"IEND", b""))


def coverage(text: str) -> tuple[str, ...]:
    """Characters of ``text`` the font cannot draw."""
    return covers(text)


def transcode(text: str, target: str = "", **options) -> Content:
    """Rasterize a prompt. The target stays text — replies are always text."""
    missing = coverage(text)
    opts = {k: v for k, v in options.items()
            if k in ("columns", "scale", "padding", "line_gap", "letter_gap", "invert")}
    page = render(text, **opts)
    fid = Fidelity(
        lossless=not missing,
        dropped=missing,
        notes=(f"{len(missing)} characters outside the bundled font were drawn as "
               f"a box; an episode whose answer depends on them is not readable "
               f"from this image",) if missing else ())
    return Content(surface="raster", text=text, target=target,
                   assets=(Asset(mime="image/png", data=png(page), role="prompt"),),
                   fidelity=fid,
                   meta={"renderer": RENDERER_VERSION, "width": page.width,
                         "height": page.height, **opts})
