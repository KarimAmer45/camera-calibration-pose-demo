from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2

from camera_pose_demo.io import load_board_config, load_calibration
from camera_pose_demo.vision import (
    draw_pose_overlay,
    estimate_chessboard_pose,
    rotation_vector_to_euler_xyz,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Estimate chessboard pose from a calibrated image.")
    parser.add_argument("--board", default="config/board.yaml", help="Path to board configuration YAML.")
    parser.add_argument("--calibration", required=True, help="Calibration YAML from calibrate-camera.")
    parser.add_argument("--image", required=True, help="Image containing the calibration target.")
    parser.add_argument("--output", default="output/pose_overlay.png", help="Annotated image output path.")
    parser.add_argument("--axis-length", type=float, default=0.12, help="Pose axis length in meters.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    board = load_board_config(args.board)
    calibration = load_calibration(args.calibration)
    inner_corners = tuple(board["inner_corners"])

    image = cv2.imread(args.image)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    found, corners, rotation_vector, translation_vector = estimate_chessboard_pose(
        image,
        calibration,
        inner_corners,
        board["square_size_m"],
    )
    if not found or corners is None or rotation_vector is None or translation_vector is None:
        raise RuntimeError("Chessboard pose could not be estimated from the image.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    overlay = draw_pose_overlay(
        image,
        corners,
        rotation_vector,
        translation_vector,
        calibration,
        args.axis_length,
        inner_corners,
    )
    cv2.imwrite(str(output_path), overlay)

    euler_deg = rotation_vector_to_euler_xyz(rotation_vector)
    result = {
        "image": args.image,
        "translation_m": translation_vector.reshape(-1).round(6).tolist(),
        "rotation_vector": rotation_vector.reshape(-1).round(6).tolist(),
        "euler_xyz_deg": [round(value, 3) for value in euler_deg],
        "overlay": str(output_path),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
