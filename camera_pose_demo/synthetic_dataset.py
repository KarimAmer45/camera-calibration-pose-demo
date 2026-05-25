from __future__ import annotations

import argparse
import random
from pathlib import Path

import cv2
import numpy as np

from camera_pose_demo.io import load_board_config


def make_chessboard_texture(inner_corners: tuple[int, int], square_px: int) -> np.ndarray:
    columns, rows = inner_corners[0] + 1, inner_corners[1] + 1
    board = np.full((rows * square_px, columns * square_px), 255, dtype=np.uint8)
    for row in range(rows):
        for column in range(columns):
            if (row + column) % 2 == 0:
                y0, y1 = row * square_px, (row + 1) * square_px
                x0, x1 = column * square_px, (column + 1) * square_px
                board[y0:y1, x0:x1] = 20
    return cv2.cvtColor(board, cv2.COLOR_GRAY2BGR)


def jittered_destination(
    image_size: tuple[int, int],
    board_size_px: tuple[int, int],
    rng: random.Random,
) -> np.ndarray:
    width, height = image_size
    board_width, board_height = board_size_px
    margin = 80

    scale = rng.uniform(0.65, 0.95)
    target_width = board_width * scale
    target_height = board_height * scale
    center_x = rng.uniform(width * 0.38, width * 0.62)
    center_y = rng.uniform(height * 0.38, height * 0.62)

    base = np.float32(
        [
            [center_x - target_width / 2, center_y - target_height / 2],
            [center_x + target_width / 2, center_y - target_height / 2],
            [center_x + target_width / 2, center_y + target_height / 2],
            [center_x - target_width / 2, center_y + target_height / 2],
        ]
    )

    perspective = min(target_width, target_height) * 0.18
    jitter = np.float32(
        [[rng.uniform(-perspective, perspective), rng.uniform(-perspective, perspective)] for _ in range(4)]
    )
    destination = base + jitter
    destination[:, 0] = np.clip(destination[:, 0], margin, width - margin)
    destination[:, 1] = np.clip(destination[:, 1], margin, height - margin)
    return destination


def render_sample(
    texture: np.ndarray,
    image_size: tuple[int, int],
    rng: random.Random,
) -> np.ndarray:
    width, height = image_size
    canvas = np.full((height, width, 3), 185, dtype=np.uint8)
    noise = rng.normalvariate(0, 1)
    if abs(noise) > 0.3:
        canvas = np.clip(canvas.astype(np.int16) + int(noise * 10), 0, 255).astype(np.uint8)

    board_height, board_width = texture.shape[:2]
    source = np.float32(
        [
            [0, 0],
            [board_width - 1, 0],
            [board_width - 1, board_height - 1],
            [0, board_height - 1],
        ]
    )
    destination = jittered_destination((width, height), (board_width, board_height), rng)
    transform = cv2.getPerspectiveTransform(source, destination)
    warped = cv2.warpPerspective(texture, transform, (width, height))
    mask = cv2.warpPerspective(
        np.full((board_height, board_width), 255, dtype=np.uint8),
        transform,
        (width, height),
    )
    canvas[mask > 0] = warped[mask > 0]

    blur = rng.choice([0, 3, 5])
    if blur:
        canvas = cv2.GaussianBlur(canvas, (blur, blur), 0)
    return canvas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic chessboard calibration frames.")
    parser.add_argument("--board", default="config/board.yaml", help="Path to board configuration YAML.")
    parser.add_argument("--output", default="data/synthetic", help="Output image directory.")
    parser.add_argument("--samples", type=int, default=24, help="Number of frames to generate.")
    parser.add_argument("--width", type=int, default=1280, help="Output image width.")
    parser.add_argument("--height", type=int, default=720, help="Output image height.")
    parser.add_argument("--square-px", type=int, default=80, help="Synthetic chessboard square size in pixels.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    board = load_board_config(args.board)
    inner_corners = tuple(board["inner_corners"])
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = random.Random(args.seed)
    texture = make_chessboard_texture(inner_corners, args.square_px)
    for index in range(args.samples):
        image = render_sample(texture, (args.width, args.height), rng)
        output_path = output_dir / f"frame_{index:03d}.png"
        cv2.imwrite(str(output_path), image)

    print(f"Wrote {args.samples} synthetic frames to {output_dir}")


if __name__ == "__main__":
    main()
