from __future__ import annotations

import argparse
import glob
from pathlib import Path

import cv2
import numpy as np

from camera_pose_demo.io import load_board_config, save_calibration
from camera_pose_demo.vision import chessboard_object_points, find_chessboard_corners


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate a camera from chessboard images.")
    parser.add_argument("--board", default="config/board.yaml", help="Path to board configuration YAML.")
    parser.add_argument("--images", required=True, help="Glob pattern for calibration images.")
    parser.add_argument("--output", default="output/calibration.yaml", help="Calibration YAML output path.")
    parser.add_argument("--preview-dir", help="Optional directory for corner preview images.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    board = load_board_config(args.board)
    inner_corners = tuple(board["inner_corners"])
    square_size_m = board["square_size_m"]
    object_template = chessboard_object_points(inner_corners, square_size_m)

    image_paths = sorted(glob.glob(args.images))
    if not image_paths:
        raise FileNotFoundError(f"No images matched pattern: {args.images}")

    object_points: list[np.ndarray] = []
    image_points: list[np.ndarray] = []
    image_size: tuple[int, int] | None = None
    preview_dir = Path(args.preview_dir) if args.preview_dir else None
    if preview_dir:
        preview_dir.mkdir(parents=True, exist_ok=True)

    for image_path in image_paths:
        image = cv2.imread(image_path)
        if image is None:
            print(f"Skipping unreadable image: {image_path}")
            continue

        found, corners, gray = find_chessboard_corners(image, inner_corners)
        image_size = (gray.shape[1], gray.shape[0])
        if not found or corners is None:
            print(f"Chessboard not found: {image_path}")
            continue

        object_points.append(object_template.copy())
        image_points.append(corners)

        if preview_dir:
            preview = image.copy()
            cv2.drawChessboardCorners(preview, inner_corners, corners, found)
            cv2.imwrite(str(preview_dir / Path(image_path).name), preview)

    if image_size is None:
        raise RuntimeError("No readable images were found.")
    if len(object_points) < 8:
        raise RuntimeError(
            f"Need at least 8 valid calibration views; found {len(object_points)}."
        )

    rms, camera_matrix, distortion, rotation_vectors, translation_vectors = cv2.calibrateCamera(
        object_points,
        image_points,
        image_size,
        None,
        None,
    )

    calibration = {
        "model": "pinhole",
        "image_size": [int(image_size[0]), int(image_size[1])],
        "camera_matrix": camera_matrix.tolist(),
        "distortion_coefficients": distortion.reshape(-1).tolist(),
        "rms_reprojection_error": float(rms),
        "valid_views": len(object_points),
        "total_images": len(image_paths),
    }
    save_calibration(args.output, calibration)
    print(f"Saved calibration to {args.output}")
    print(f"RMS reprojection error: {rms:.4f}")
    print(f"Valid views: {len(object_points)} / {len(image_paths)}")


if __name__ == "__main__":
    main()
