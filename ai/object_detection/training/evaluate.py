"""Evaluate a trained detector checkpoint on a dataset split.

Entry point:
    python -m ai.object_detection.training.evaluate [--weights PATH] [--split {val,test}]

Defaults to the best weights from the newest training run and the
validation split. Reports mAP@50, mAP@50-95, precision, and recall.
"""
import argparse
from pathlib import Path

from ai.object_detection.config import ConfigError, load_dataset_config, load_model_config
from ai.object_detection.paths import CHECKPOINTS_DIR
from ai.shared.utils.device import select_device
from ai.shared.utils.experiment import find_weights
from ai.shared.utils.logger import get_logger
from ai.object_detection.training.train import load_yolo_class, write_resolved_dataset_yaml

logger = get_logger("training.evaluate")

VALID_SPLITS = ("val", "test")


def resolve_weights(weights: str | None) -> Path:
    """Resolve the weights argument to an existing checkpoint file.

    Args:
        weights: Explicit path, or None to use the newest run's best.pt.

    Returns:
        Path to the weights file.

    Raises:
        ConfigError: If no weights are found.
    """
    if weights:
        path = Path(weights)
        if not path.is_file():
            raise ConfigError(f"Weights file not found: {path}")
        return path
    found = find_weights("best", CHECKPOINTS_DIR)
    if found is None:
        raise ConfigError(
            "No trained weights found under ai/object_detection/models/checkpoints/. "
            "Train a model first or pass --weights."
        )
    return found


def extract_metrics(results) -> dict[str, float]:
    """Pull the headline detection metrics out of Ultralytics val results.

    Args:
        results: The object returned by YOLO.val().

    Returns:
        Mapping with mAP50, mAP50-95, precision, and recall.
    """
    box = results.box
    return {
        "mAP50": float(box.map50),
        "mAP50-95": float(box.map),
        "precision": float(box.mp),
        "recall": float(box.mr),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list; None uses sys.argv.

    Returns:
        Parsed namespace with 'weights' and 'split'.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--weights", default=None,
        help="Checkpoint to evaluate; defaults to the newest run's best.pt",
    )
    parser.add_argument(
        "--split", default="val", choices=VALID_SPLITS,
        help="Dataset split to evaluate on (default: val)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, float]:
    """Run evaluation and return the extracted metrics.

    Args:
        argv: Argument list; None uses sys.argv.

    Returns:
        The metrics mapping from extract_metrics().
    """
    args = parse_args(argv)
    weights = resolve_weights(args.weights)
    dataset = load_dataset_config()
    model_cfg = load_model_config()
    device = select_device(model_cfg.device)

    run_dir = weights.parent.parent
    data_yaml = write_resolved_dataset_yaml(dataset, run_dir)

    yolo_class = load_yolo_class()
    model = yolo_class(str(weights))
    logger.info("Evaluating | weights=%s split=%s device=%s", weights, args.split, device)

    results = model.val(
        data=str(data_yaml),
        split=args.split,
        conf=model_cfg.confidence_threshold,
        iou=model_cfg.iou_threshold,
        device=device,
    )
    metrics = extract_metrics(results)
    for name, value in metrics.items():
        logger.info("%-10s %.4f", name, value)
    return metrics


if __name__ == "__main__":
    main()
