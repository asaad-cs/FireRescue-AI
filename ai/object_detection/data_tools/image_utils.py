"""Standard-library image probing and content hashing.

Reads only file headers to determine format and pixel dimensions, so
validation runs fast on thousands of images and needs no ML stack.
An optional deep check (full decode) uses cv2 when it is installed.
"""
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

# Must stay aligned with the extensions predict.py accepts.
SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# JPEG start-of-frame markers that carry the image dimensions.
_JPEG_SOF_MARKERS = frozenset(
    range(0xC0, 0xD0)) - {0xC4, 0xC8, 0xCC}


class ImageError(ValueError):
    """An image file is unsupported, truncated, or corrupted."""


@dataclass(frozen=True)
class ImageInfo:
    """Header-level facts about an image file."""

    width: int
    height: int
    format: str


def probe_image(path: Path) -> ImageInfo:
    """Read an image header and return its format and dimensions.

    Args:
        path: Image file to probe.

    Returns:
        ImageInfo with positive width/height.

    Raises:
        ImageError: If the extension is unsupported or the header is
            missing, truncated, or inconsistent with the extension.
    """
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ImageError(f"unsupported image format '{ext}': {path.name}")
    try:
        with path.open("rb") as fh:
            if ext == ".png":
                info = _probe_png(fh.read(33))
            elif ext == ".bmp":
                info = _probe_bmp(fh.read(30))
            else:
                info = _probe_jpeg(fh)
    except OSError as exc:
        raise ImageError(f"unreadable image {path.name}: {exc}") from exc
    if info.width <= 0 or info.height <= 0:
        raise ImageError(
            f"invalid dimensions {info.width}x{info.height}: {path.name}"
        )
    return info


def decode_check(path: Path) -> bool:
    """Fully decode an image with cv2 if cv2 is available.

    Args:
        path: Image file to decode.

    Returns:
        False only when cv2 is installed and fails to decode the file;
        True otherwise (including when cv2 is not installed).
    """
    try:
        import cv2  # noqa: PLC0415 — heavy import stays lazy
        import numpy as np  # noqa: PLC0415
    except ImportError:
        return True
    # imdecode instead of imread: imread cannot handle non-ASCII
    # Windows paths.
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR) is not None


def file_hash(path: Path, algorithm: str = "md5") -> str:
    """Hash a file's content in chunks.

    Args:
        path: File to hash.
        algorithm: Any hashlib algorithm name.

    Returns:
        The lowercase hex digest.
    """
    digest = hashlib.new(algorithm)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _probe_png(header: bytes) -> ImageInfo:
    if len(header) < 24 or not header.startswith(_PNG_SIGNATURE):
        raise ImageError("not a valid PNG header")
    if header[12:16] != b"IHDR":
        raise ImageError("PNG missing IHDR chunk")
    width, height = struct.unpack(">II", header[16:24])
    return ImageInfo(width=width, height=height, format="png")


def _probe_bmp(header: bytes) -> ImageInfo:
    if len(header) < 26 or not header.startswith(b"BM"):
        raise ImageError("not a valid BMP header")
    width, height = struct.unpack("<ii", header[18:26])
    # Top-down BMPs store a negative height.
    return ImageInfo(width=width, height=abs(height), format="bmp")


def _probe_jpeg(fh) -> ImageInfo:
    if fh.read(2) != b"\xff\xd8":
        raise ImageError("not a valid JPEG header")
    while True:
        marker = fh.read(2)
        if len(marker) < 2:
            raise ImageError("truncated JPEG: no start-of-frame marker")
        if marker[0] != 0xFF:
            raise ImageError("corrupted JPEG marker stream")
        code = marker[1]
        if code == 0xD9:  # EOI before any SOF
            raise ImageError("truncated JPEG: no start-of-frame marker")
        if code in (0x01,) or 0xD0 <= code <= 0xD7:  # standalone markers
            continue
        length_bytes = fh.read(2)
        if len(length_bytes) < 2:
            raise ImageError("truncated JPEG segment")
        (length,) = struct.unpack(">H", length_bytes)
        if length < 2:
            raise ImageError("corrupted JPEG segment length")
        if code in _JPEG_SOF_MARKERS:
            body = fh.read(5)
            if len(body) < 5:
                raise ImageError("truncated JPEG start-of-frame")
            height, width = struct.unpack(">HH", body[1:5])
            return ImageInfo(width=width, height=height, format="jpeg")
        fh.seek(length - 2, 1)
