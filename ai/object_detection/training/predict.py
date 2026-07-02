"""Run detector inference on an image or a folder of images.

Entry point:
    python -m ai.object_detection.training.predict --source PATH
        [--weights PATH] [--conf FLOAT] [--save-dir PATH]

Annotated prediction images are saved to a timestamped directory under
ai/object_detection/models/predictions/ by default. No webcam or video
support.
"""
import argparse
from pathlib import Path

from ai.object_detection.config import ConfigError, load_model_config
from ai.object_detection.paths import MODELS_DIR
from ai.shared.utils.device import select_device
from ai.shared.utils.experiment import make_run_name
from ai.shared.utils.logger import get_logger
from ai.object_detection.training.evaluate import resolve_weights
from ai.object_detection.training.train import load_yolo_class

logger = get_logger("training.predict")

PREDICTIONS_DIR = MODELS_DIR / "predictions"
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")


def validate_source(source: str) -> Path:
    """Check that the inference source is a usable image or folder.

    Args:
        source: Path to a single image or a directory of images.

    Returns:
        The validated path.

    Raises:
        ConfigError: If the path is missing, an unsupported file type,
            or a folder containing no images.
    """
    path = Path(source)
    if path.is_file():
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ConfigError(
                f"Unsupported image type '{path.suffix}'. "
                f"Supported: {', '.join(IMAGE_EXTENSIONS)}"
            )
        return path
    if path.is_dir():
        has_images = any(
            p.suffix.lower() in IMAGE_EXTENSIONS for p in path.iterdir() if p.is_file()
        )
        if not has_images:
            raise ConfigError(f"Folder contains no supported images: {path}")
        return path
    raise ConfigError(f"Source not found: {path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list; None uses sys.argv.

    Returns:
        Parsed namespace with source, weights, conf, and save_dir.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", required=True, help="Image file or folder of images"
    )
    parser.add_argument(
        "--weights", default=None,
        help="Checkpoint to use; defaults to the newest run's best.pt",
    )
    parser.add_argument(
        "--conf", type=float, default=None,
        help="Confidence threshold; defaults to model.yaml's value",
    )
    parser.add_argument(
        "--save-dir", default=None,
        help="Output root for annotated images (default: ai/object_detection/models/predictions/)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> Path:
    """Run inference and save annotated images.

    Args:
        argv: Argument list; None uses sys.argv.

    Returns:
        The directory the annotated images were written to.
    """
    args = parse_args(argv)
    source = validate_source(args.source)
    weights = resolve_weights(args.weights)
    model_cfg = load_model_config()

    conf = args.conf if args.conf is not None else model_cfg.confidence_threshold
    if not 0.0 < conf < 1.0:
        raise ConfigError(f"Confidence threshold must be between 0 and 1, got {conf}")

    device = select_device(model_cfg.device)
    save_root = Path(args.save_dir) if args.save_dir else PREDICTIONS_DIR
    run_name = make_run_name("predict")

    yolo_class = load_yolo_class()
    model = yolo_class(str(weights))
    logger.info(
        "Predicting | source=%s weights=%s conf=%.2f device=%s",
        source, weights, conf, device,
    )
    model.predict(
        source=str(source),
        conf=conf,
        iou=model_cfg.iou_threshold,
        device=device,
        save=True,
        project=str(save_root),
        name=run_name,
        exist_ok=True,
    )
    out_dir = save_root / run_name
    logger.info("Predictions saved | %s", out_dir)
    return out_dir


if __name__ == "__main__":
    main()
