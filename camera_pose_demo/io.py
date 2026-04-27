from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_board_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)

    board = config.get("board", config)
    if board.get("type") != "chessboard":
        raise ValueError("Only chessboard targets are supported by this demo.")

    inner_corners = board.get("inner_corners")
    square_size_m = board.get("square_size_m")
    if not inner_corners or len(inner_corners) != 2:
        raise ValueError("board.inner_corners must contain [columns, rows].")
    if not square_size_m or square_size_m <= 0:
        raise ValueError("board.square_size_m must be a positive number.")

    return {
        "type": "chessboard",
        "inner_corners": [int(inner_corners[0]), int(inner_corners[1])],
        "square_size_m": float(square_size_m),
    }


def save_calibration(path: str | Path, calibration: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(calibration, stream, sort_keys=False)


def load_calibration(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as stream:
        calibration = yaml.safe_load(stream)

    required = {"camera_matrix", "distortion_coefficients", "image_size"}
    missing = required.difference(calibration)
    if missing:
        missing_names = ", ".join(sorted(missing))
        raise ValueError(f"Calibration file is missing: {missing_names}")

    return calibration
