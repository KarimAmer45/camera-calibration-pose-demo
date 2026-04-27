from __future__ import annotations

import cv2
import numpy as np

from camera_pose_demo.io import load_board_config
from camera_pose_demo.vision import (
    draw_pose_overlay,
    estimate_chessboard_pose,
    rotation_matrix_to_quaternion,
)


def main() -> None:
    try:
        import rclpy
        from cv_bridge import CvBridge
        from geometry_msgs.msg import PoseStamped
        from rclpy.node import Node
        from sensor_msgs.msg import CameraInfo, Image
    except ImportError as error:
        raise SystemExit(
            "ROS 2 dependencies are not available. Build this package in a ROS 2 "
            "environment to run ros-board-pose-node."
        ) from error

    class BoardPoseNode(Node):
        def __init__(self) -> None:
            super().__init__("board_pose_node")
            self.declare_parameter("board_config", "config/board.yaml")
            self.declare_parameter("image_topic", "/demo/camera/image_raw")
            self.declare_parameter("camera_info_topic", "/demo/camera/camera_info")
            self.declare_parameter("pose_topic", "/camera_pose_demo/board_pose")
            self.declare_parameter("debug_image_topic", "/camera_pose_demo/debug_image")
            self.declare_parameter("axis_length_m", 0.12)

            board_config = self.get_parameter("board_config").value
            self.board = load_board_config(board_config)
            self.inner_corners = tuple(self.board["inner_corners"])
            self.axis_length_m = float(self.get_parameter("axis_length_m").value)
            self.bridge = CvBridge()
            self.calibration: dict[str, object] | None = None

            image_topic = self.get_parameter("image_topic").value
            camera_info_topic = self.get_parameter("camera_info_topic").value
            pose_topic = self.get_parameter("pose_topic").value
            debug_image_topic = self.get_parameter("debug_image_topic").value

            self.pose_pub = self.create_publisher(PoseStamped, pose_topic, 10)
            self.debug_pub = self.create_publisher(Image, debug_image_topic, 10)
            self.create_subscription(CameraInfo, camera_info_topic, self.on_camera_info, 10)
            self.create_subscription(Image, image_topic, self.on_image, 10)
            self.get_logger().info(f"Estimating board pose from {image_topic}")

        def on_camera_info(self, message: CameraInfo) -> None:
            self.calibration = {
                "camera_matrix": np.asarray(message.k, dtype=np.float64).reshape(3, 3).tolist(),
                "distortion_coefficients": list(message.d),
                "image_size": [message.width, message.height],
            }

        def on_image(self, message: Image) -> None:
            if self.calibration is None:
                self.get_logger().debug("Waiting for camera info.")
                return

            image = self.bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
            found, corners, rotation_vector, translation_vector = estimate_chessboard_pose(
                image,
                self.calibration,
                self.inner_corners,
                self.board["square_size_m"],
            )
            if not found or corners is None or rotation_vector is None or translation_vector is None:
                return

            pose = PoseStamped()
            pose.header = message.header
            pose.header.frame_id = message.header.frame_id or "camera_link"
            translation = translation_vector.reshape(-1)
            pose.pose.position.x = float(translation[0])
            pose.pose.position.y = float(translation[1])
            pose.pose.position.z = float(translation[2])

            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            qx, qy, qz, qw = rotation_matrix_to_quaternion(rotation_matrix)
            pose.pose.orientation.x = qx
            pose.pose.orientation.y = qy
            pose.pose.orientation.z = qz
            pose.pose.orientation.w = qw
            self.pose_pub.publish(pose)

            annotated = draw_pose_overlay(
                image,
                corners,
                rotation_vector,
                translation_vector,
                self.calibration,
                self.axis_length_m,
                self.inner_corners,
            )
            self.debug_pub.publish(self.bridge.cv2_to_imgmsg(annotated, encoding="bgr8"))

    rclpy.init()
    node = BoardPoseNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
