from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np


def chessboard_object_points(inner_corners: tuple[int, int], square_size_m: float) -> np.ndarray:
    columns, rows = inner_corners
    points = np.zeros((columns * rows, 3), np.float32)
    points[:, :2] = np.mgrid[0:columns, 0:rows].T.reshape(-1, 2)
    points *= square_size_m
    return points


def find_chessboard_corners(
    image: np.ndarray,
    inner_corners: tuple[int, int],
) -> tuple[bool, np.ndarray | None, np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    flags = cv2.CALIB_CB_ADAPTIVE_THRESH | cv2.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv2.findChessboardCorners(gray, inner_corners, flags)
    if not found:
        return False, None, gray

    criteria = (
        cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
        30,
        0.001,
    )
    refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    return True, refined, gray


def estimate_chessboard_pose(
    image: np.ndarray,
    calibration: dict[str, Any],
    inner_corners: tuple[int, int],
    square_size_m: float,
) -> tuple[bool, np.ndarray | None, np.ndarray | None, np.ndarray | None]:
    found, corners, _ = find_chessboard_corners(image, inner_corners)
    if not found or corners is None:
        return False, None, None, None

    object_points = chessboard_object_points(inner_corners, square_size_m)
    camera_matrix = np.asarray(calibration["camera_matrix"], dtype=np.float64)
    distortion = np.asarray(calibration["distortion_coefficients"], dtype=np.float64)

    ok, rotation_vector, translation_vector = cv2.solvePnP(
        object_points,
        corners,
        camera_matrix,
        distortion,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not ok:
        return False, corners, None, None
    return True, corners, rotation_vector, translation_vector


def draw_pose_overlay(
    image: np.ndarray,
    corners: np.ndarray,
    rotation_vector: np.ndarray,
    translation_vector: np.ndarray,
    calibration: dict[str, Any],
    axis_length_m: float,
    inner_corners: tuple[int, int],
) -> np.ndarray:
    annotated = image.copy()
    cv2.drawChessboardCorners(annotated, inner_corners, corners, True)
    camera_matrix = np.asarray(calibration["camera_matrix"], dtype=np.float64)
    distortion = np.asarray(calibration["distortion_coefficients"], dtype=np.float64)
    cv2.drawFrameAxes(
        annotated,
        camera_matrix,
        distortion,
        rotation_vector,
        translation_vector,
        axis_length_m,
        3,
    )
    return annotated


def rotation_vector_to_euler_xyz(rotation_vector: np.ndarray) -> tuple[float, float, float]:
    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    sy = math.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
    singular = sy < 1e-6

    if singular:
        x = math.atan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
        y = math.atan2(-rotation_matrix[2, 0], sy)
        z = 0.0
    else:
        x = math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
        y = math.atan2(-rotation_matrix[2, 0], sy)
        z = math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])

    return math.degrees(x), math.degrees(y), math.degrees(z)


def rotation_matrix_to_quaternion(rotation_matrix: np.ndarray) -> tuple[float, float, float, float]:
    trace = float(np.trace(rotation_matrix))
    if trace > 0:
        scale = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * scale
        qx = (rotation_matrix[2, 1] - rotation_matrix[1, 2]) / scale
        qy = (rotation_matrix[0, 2] - rotation_matrix[2, 0]) / scale
        qz = (rotation_matrix[1, 0] - rotation_matrix[0, 1]) / scale
    elif rotation_matrix[0, 0] > rotation_matrix[1, 1] and rotation_matrix[0, 0] > rotation_matrix[2, 2]:
        scale = math.sqrt(1.0 + rotation_matrix[0, 0] - rotation_matrix[1, 1] - rotation_matrix[2, 2]) * 2.0
        qw = (rotation_matrix[2, 1] - rotation_matrix[1, 2]) / scale
        qx = 0.25 * scale
        qy = (rotation_matrix[0, 1] + rotation_matrix[1, 0]) / scale
        qz = (rotation_matrix[0, 2] + rotation_matrix[2, 0]) / scale
    elif rotation_matrix[1, 1] > rotation_matrix[2, 2]:
        scale = math.sqrt(1.0 + rotation_matrix[1, 1] - rotation_matrix[0, 0] - rotation_matrix[2, 2]) * 2.0
        qw = (rotation_matrix[0, 2] - rotation_matrix[2, 0]) / scale
        qx = (rotation_matrix[0, 1] + rotation_matrix[1, 0]) / scale
        qy = 0.25 * scale
        qz = (rotation_matrix[1, 2] + rotation_matrix[2, 1]) / scale
    else:
        scale = math.sqrt(1.0 + rotation_matrix[2, 2] - rotation_matrix[0, 0] - rotation_matrix[1, 1]) * 2.0
        qw = (rotation_matrix[1, 0] - rotation_matrix[0, 1]) / scale
        qx = (rotation_matrix[0, 2] + rotation_matrix[2, 0]) / scale
        qy = (rotation_matrix[1, 2] + rotation_matrix[2, 1]) / scale
        qz = 0.25 * scale

    return float(qx), float(qy), float(qz), float(qw)
