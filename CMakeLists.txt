cmake_minimum_required(VERSION 2.8.3)
project(stalkerbot)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  sensor_msgs
  std_msgs
  message_generation
  actionlib_msgs
  fiducial_msgs
)

add_message_files(
   FILES
   location_info.msg
   filtered_transform.msg )

# add_service_files(
#   FILES
#   Service1.srv
#   Service2.srv
# )

add_action_files(
    FILES
    Search.action
)

generate_messages(
    DEPENDENCIES
    std_msgs
    actionlib_msgs
    fiducial_msgs
)

catkin_package(
  CATKIN_DEPENDS actionlib_msgs
  CATKIN_DEPENDS message_runtime
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)