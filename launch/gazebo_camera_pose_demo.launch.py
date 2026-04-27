from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    package_share = FindPackageShare("camera_pose_demo")
    gazebo_share = FindPackageShare("gazebo_ros")

    default_world = PathJoinSubstitution(
        [package_share, "gazebo", "worlds", "camera_pose_lab.world"]
    )
    default_board_config = PathJoinSubstitution([package_share, "config", "board.yaml"])
    default_robot = PathJoinSubstitution([package_share, "urdf", "camera_rig.urdf.xacro"])
    model_path = PathJoinSubstitution([package_share, "gazebo", "models"])

    world = LaunchConfiguration("world")
    board_config = LaunchConfiguration("board_config")
    robot_model = LaunchConfiguration("robot_model")

    robot_description = {
        "robot_description": Command(["xacro ", robot_model]),
    }

    return LaunchDescription(
        [
            DeclareLaunchArgument("world", default_value=default_world),
            DeclareLaunchArgument("board_config", default_value=default_board_config),
            DeclareLaunchArgument("robot_model", default_value=default_robot),
            SetEnvironmentVariable(
                "GAZEBO_MODEL_PATH",
                [model_path, ":", EnvironmentVariable("GAZEBO_MODEL_PATH", default_value="")],
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    [PathJoinSubstitution([gazebo_share, "launch", "gazebo.launch.py"])]
                ),
                launch_arguments={"world": world}.items(),
            ),
            Node(
                package="robot_state_publisher",
                executable="robot_state_publisher",
                parameters=[robot_description],
                output="screen",
            ),
            Node(
                package="gazebo_ros",
                executable="spawn_entity.py",
                arguments=["-topic", "robot_description", "-entity", "camera_pose_demo"],
                output="screen",
            ),
            Node(
                package="camera_pose_demo",
                executable="ros-board-pose-node",
                parameters=[
                    {
                        "board_config": board_config,
                        "image_topic": "/demo/camera/image_raw",
                        "camera_info_topic": "/demo/camera/camera_info",
                        "pose_topic": "/camera_pose_demo/board_pose",
                        "debug_image_topic": "/camera_pose_demo/debug_image",
                    }
                ],
                output="screen",
            ),
        ]
    )
