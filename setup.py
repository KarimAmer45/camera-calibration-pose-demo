from glob import glob
from setuptools import find_packages, setup

package_name = "camera_pose_demo"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml", "README.md"]),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/urdf", glob("urdf/*.urdf.xacro")),
        (f"share/{package_name}/gazebo/worlds", glob("gazebo/worlds/*.world")),
        (
            f"share/{package_name}/gazebo/models/calibration_checkerboard",
            glob("gazebo/models/calibration_checkerboard/*"),
        ),
    ],
    install_requires=["setuptools", "numpy", "opencv-python", "PyYAML"],
    zip_safe=True,
    maintainer="Camera Pose Demo Maintainer",
    maintainer_email="maintainer@example.com",
    description="Camera calibration and chessboard pose estimation demo with Gazebo simulation assets.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "calibrate-camera = camera_pose_demo.calibrate_camera:main",
            "estimate-board-pose = camera_pose_demo.estimate_pose:main",
            "make-synthetic-dataset = camera_pose_demo.synthetic_dataset:main",
            "ros-board-pose-node = camera_pose_demo.ros_pose_node:main",
        ],
    },
)
