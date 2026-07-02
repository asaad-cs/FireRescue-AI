"""Synthetic file factories for dataset tool tests.

Builds tiny but structurally valid images and label files with the
standard library only, so tests never need real datasets or the ML
stack. Not a test module (leading underscore keeps pytest away).
"""
import struct
import zlib
from pathlib import Path


def make_png(width: int = 4, height: int = 4,
             color: tuple[int, int, int] = (255, 0, 0)) -> bytes:
    """A fully valid, decodable RGB PNG."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body)))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def make_bmp(width: int = 4, height: int = 4) -> bytes:
    """A minimal 24-bit BMP with a valid header."""
    row = (b"\x00" * (width * 3 + (4 - width * 3 % 4) % 4))
    pixels = row * height
    header = (b"BM" + struct.pack("<IHHI", 54 + len(pixels), 0, 0, 54)
              + struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24, 0,
                            len(pixels), 0, 0, 0, 0))
    return header + pixels


def make_jpeg_header(width: int = 4, height: int = 4) -> bytes:
    """JPEG bytes with valid SOI/APP0/SOF0 markers (header-parseable)."""
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    sof0_body = struct.pack(">BHHB", 8, height, width, 3) + b"\x00" * 9
    sof0 = b"\xff\xc0" + struct.pack(">H", len(sof0_body) + 2) + sof0_body
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


def write_image(path: Path, width: int = 4, height: int = 4,
                color: tuple[int, int, int] = (255, 0, 0)) -> Path:
    """Write a valid image of the format implied by the extension."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ext = path.suffix.lower()
    if ext == ".png":
        path.write_bytes(make_png(width, height, color))
    elif ext == ".bmp":
        path.write_bytes(make_bmp(width, height))
    else:
        path.write_bytes(make_jpeg_header(width, height))
    return path


def write_label(path: Path, lines: list[str]) -> Path:
    """Write a YOLO label file from raw lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""),
                    encoding="utf-8")
    return path


def build_yolo_source(root: Path, split: str,
                      entries: dict[str, list[str] | None]) -> Path:
    """Create <root>/<split>/images + labels from {stem: label lines}.

    Every image gets unique pixel content (derived from its stem) so
    merge deduplication is never triggered by accident; tests create
    intentional duplicates by copying bytes explicitly. A None value
    skips the label file (an orphan image); label lines are written
    verbatim so tests can inject malformed content.
    """
    for stem, lines in entries.items():
        color = unique_color(f"{root.name}/{split}/{stem}")
        write_image(root / split / "images" / f"{stem}.png", color=color)
        if lines is not None:
            write_label(root / split / "labels" / f"{stem}.txt", lines)
    return root


def unique_color(key: str) -> tuple[int, int, int]:
    """A deterministic RGB color derived from an arbitrary string."""
    h = zlib.crc32(key.encode())
    return (h & 0xFF, (h >> 8) & 0xFF, (h >> 16) & 0xFF)
