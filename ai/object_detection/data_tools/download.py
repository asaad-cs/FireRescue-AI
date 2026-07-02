"""Download raw source datasets into datasets/raw/.

Every automatable source is fetched with a checksum verification and
unpacked next to its archive. Sources that require a login (D-Fire's
OneDrive/Kaggle hosting) are listed with pointers to the manual steps
in docs/download_instructions.md — their absence never fails the run.

    python -m ai.object_detection.data_tools.download            # all
    python -m ai.object_detection.data_tools.download --source coco_person_images
"""
import argparse
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ai.object_detection.data_tools.image_utils import file_hash
from ai.object_detection.paths import DOCS_DIR, RAW_DATA_DIR
from ai.shared.utils.logger import get_logger

log = get_logger("data_tools.download")

_CHUNK = 1 << 20  # 1 MiB


@dataclass(frozen=True)
class DownloadSpec:
    """One directly downloadable archive."""

    name: str
    url: str
    # Destination, relative to datasets/raw/.
    dest: str
    md5: str
    extract_to: str | None = None


DOWNLOADS = (
    DownloadSpec(
        name="figshare_fire_smoke",
        url="https://ndownloader.figshare.com/files/53486522",
        dest="figshare_fire_smoke/MyData_Fire.zip",
        md5="fd9ed42cd67fd5f7c016ca127985e245",
        extract_to="figshare_fire_smoke/extracted",
    ),
    DownloadSpec(
        name="coco_person_images",
        url="http://images.cocodataset.org/zips/val2017.zip",
        dest="coco_person/val2017.zip",
        md5="442b8da7639aecaf257c1dceb8ba8c80",
        extract_to="coco_person",
    ),
    DownloadSpec(
        name="coco_person_annotations",
        url="http://images.cocodataset.org/annotations/"
            "annotations_trainval2017.zip",
        dest="coco_person/annotations_trainval2017.zip",
        md5="f4bbac642086de4f52a3fdda2de5fa2c",
        extract_to="coco_person",
    ),
)

# Sources that cannot be fetched without a login. The merge pipeline
# skips them until their files appear under datasets/raw/.
MANUAL_SOURCES = ("dfire (OneDrive/Kaggle — see docs/download_instructions.md)",)


def download_file(url: str, dest: Path, expected_md5: str | None = None) -> Path:
    """Download one file, verifying its checksum.

    An existing destination with a matching checksum is kept as-is, so
    re-running the downloader is cheap and idempotent.

    Args:
        url: Source URL.
        dest: Destination file; parent directories are created.
        expected_md5: Checksum to enforce; None skips verification.

    Returns:
        The destination path.

    Raises:
        RuntimeError: If the downloaded file fails checksum verification.
    """
    if dest.is_file() and expected_md5 and file_hash(dest) == expected_md5:
        log.info("already downloaded and verified: %s", dest.name)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    log.info("downloading %s -> %s", url, dest)
    partial = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(url) as response, partial.open("wb") as out:
        while True:
            chunk = response.read(_CHUNK)
            if not chunk:
                break
            out.write(chunk)
    if expected_md5:
        actual = file_hash(partial)
        if actual != expected_md5:
            partial.unlink()
            raise RuntimeError(
                f"checksum mismatch for {dest.name}: expected "
                f"{expected_md5}, got {actual}"
            )
    partial.replace(dest)
    log.info("downloaded and verified: %s", dest.name)
    return dest


def extract_zip(archive: Path, dest_dir: Path) -> Path:
    """Unpack a zip archive, skipping when already extracted.

    Args:
        archive: Zip file to unpack.
        dest_dir: Extraction directory; created if missing.

    Returns:
        The extraction directory.
    """
    with zipfile.ZipFile(archive) as zf:
        members = zf.namelist()
        if members and all(
            (dest_dir / m).exists() for m in members[:20]
        ):
            log.info("already extracted: %s", archive.name)
            return dest_dir
        log.info("extracting %s (%d entries) -> %s",
                 archive.name, len(members), dest_dir)
        zf.extractall(dest_dir)
    return dest_dir


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: fetch and unpack all automatable sources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=[d.name for d in DOWNLOADS],
        help="download a single source instead of all",
    )
    args = parser.parse_args(argv)

    for spec in DOWNLOADS:
        if args.source and spec.name != args.source:
            continue
        dest = RAW_DATA_DIR / spec.dest
        download_file(spec.url, dest, spec.md5)
        if spec.extract_to:
            extract_zip(dest, RAW_DATA_DIR / spec.extract_to)

    if not args.source:
        for manual in MANUAL_SOURCES:
            log.info("manual download required: %s", manual)
        log.info("instructions: %s", DOCS_DIR / "download_instructions.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
