import cv2
import math
import numpy as np
from time import time_ns

from super_map import LazyDict
from subsystems.vision_position_estimation import a_pattern, b_pattern, c_pattern, d_pattern, e_pattern, add_marker, \
    rotation_matrix_to_euler_angles, id_to_letter
#TODO rework this so that it's pulling from the main kalman filter script
#NOTE should probably change how this structured 
from subsystems.vision_position_estimation import KalmanFilter2D
from subsystems.video_stream import video_stream
from toolbox.globals import config, runtime
from toolbox.geometry_tools import Position, BoundingBox
from toolbox.distance_xyz import get_dist_to_bbox, get_xyz_at_color_coords

#TODO figure out what to do if we detect multiple markers or if that's even possible
#? is LazyDict necessary
runtime.camera_position = LazyDict(
    marker_patterns = [],
    marker_colors = [],
    marker_contours = [],
    realsense_robot_coord = [],
    vision_robot_coord = []
)

#
# Config
#
MIN_RANGE           = config.aiming.min_range
MAX_RANGE           = config.aiming.max_range
DEPTH_COMPATIBLE    = config.hardware.camera_has_depth

#TODO figure out how to use realsense api to get intrinsics
#TODO add get_instrinsics to videostream class
calib_data_path = "./subsystems/Juan_Cal_Matrix.npz"

calib_data = np.load(calib_data_path)

cam_mat = calib_data["camMatrix"]
dist_coef = calib_data["distCoef"]

MARKER_SIZE = 140 # mm



# define an empty custom dictionary with
aruco_dict = cv2.aruco.Dictionary(0, 5)

# add empty bytesList array to fill with
aruco_dict.bytesList = np.empty(shape=(5, 4, 4), dtype=np.uint8)

add_marker(aruco_dict, 0, a_pattern)
add_marker(aruco_dict, 1, b_pattern)
add_marker(aruco_dict, 2, c_pattern)
add_marker(aruco_dict, 3, d_pattern)
add_marker(aruco_dict, 4, e_pattern)

parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)

def when_frame_arrives():
    global past_time
    # import current frame
    frame = runtime.color_image
    # reset runtime variable
    runtime.camera_position.marker_patterns = []
    runtime.camera_position.marker_colors = []
    runtime.camera_position.marker_contours = []
    runtime.camera_position.realsense_robot_coord = []
    runtime.camera_position.vision_robot_coord = []
    #? should we do it like about or reset it like this |
    #?                                                  v
    vision_robot_coord = []

    # ? is this necessary
    if frame is not None:
        # detect markers
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        marker_corners, marker_IDs, rejects = detector.detectMarkers(gray_frame)
        # get 3d raw coords
        #realsense_marker_3ds = use_realsense_depth(marker_corners)
        vision_marker_3ds = use_vision_depth(marker_corners)
   
        # filter 3d coord
        # ! only works for detecting one marker
        # TODO implement realsense depth and uncomment realsense stuff
        if vision_marker_3ds: #realsense_marker_3ds or
            # ? filter after or before we get robot coords?
            print("\n",vision_marker_3ds)
            # Detect marker colors
            detected_colors = [] 
            for ids, corners in zip(marker_IDs, marker_corners):
                cv2.polylines(frame, [corners.astype(np.int32)], True, (0, 255, 255), 4, cv2.LINE_AA)
                corners = corners.reshape(4, 2).astype(np.int32)
                top_right, top_left, bottom_right, bottom_left = corners[0], corners[1], corners[2], corners[3]
                #TODO try changing this to just one set of marker corners
                # Define the parallelogram region using the four corner points
                parallelogram_points = np.array([top_right, top_left, bottom_left, bottom_right], dtype=np.int32)

                # Create a mask for the parallelogram region
                mask = np.zeros(frame.shape[:2], dtype=np.uint8)
                cv2.fillPoly(mask, [parallelogram_points], color=255)

                # Compute the mean color within the masked region
                mean_color = cv2.mean(frame, mask=mask)[:3]

                #!NOTE this needs extensive testing
                detected_color = "N/A"
                if mean_color[0] > 125:
                    detected_color = "Blue"
                elif mean_color[2] > 125:
                    detected_color = "Red"
                detected_colors.append(detected_color)

            # export all runtime variables
            #!!! new runtime variables
            runtime.camera_position.marker_patterns = [id_to_letter[id] for id in ids]
            runtime.camera_position.marker_colors = detected_colors
            runtime.camera_position.vision_robot_coord = vision_robot_coord

        #TODO decide on a name between marker_contours, marker_corners, or marker_outlines
        runtime.camera_position.marker_contours = marker_corners



#TODO change this so that the if statement is outside the function
def use_vision_depth(marker_corners):
    if marker_corners:
        marker_3d_coords = []
        for marker_corner in marker_corners: 
            rVec, tVec, _ = cv2.aruco.estimatePoseSingleMarkers(marker_corner, MARKER_SIZE, cam_mat, dist_coef)

            rVec = rVec[0][0]
            tVec = tVec[0][0]

            rVec_flipped = rVec * -1
            tVec_flipped = tVec * -1

            rotation_matrix, jacobian = cv2.Rodrigues(rVec_flipped)
            # ! this needs to be converter into meters somewhere
            proper_tVec = np.dot(rotation_matrix, tVec_flipped)
            # transforms 3d coords to agreed upon frame of reference for camera
            # ! assuming tVec is in millimeters
            #TODO figure out how to see if we're using realsense
            #TODO add name attribute to video stream
            # marker_3d_coord = video_stream.retransform_3d_point_to_coordinate_system(proper_tVec)
            # marker_3d_coord = video_stream.offset_3d_point_to_camera_center(marker_3d_coord)

            marker_3d_coords.append(proper_tVec)
        
        return marker_3d_coords

# def use_realsense_depth(marker_corners):
#       if DEPTH_COMPATIBLE and marker_corners:
#         marker_3d_coords = []
#         marker_bboxes = get_bounding_boxes(marker_corners)
#         for marker_bbox in marker_bboxes:
#             # TODO: make min and max range constants in config for marker detection
#             # instead of armor plate detection
#
#             # check all of the bounding boxes, remove invalid ones if outside ranges
#             sampled_depth = get_dist_to_bbox(marker_bbox)
#             if sampled_depth is None:
#                 continue
#             elif sampled_depth < MIN_RANGE:
#                 continue
#             elif sampled_depth > MAX_RANGE:
#                 continue
#             else:
#                 # ! might need .item()
#                 marker_3d_coord = get_xyz_at_color_coords([marker_bbox.center[0], marker_bbox.center[1]], sampled_depth)
#                 if marker_3d_coord is None:
#                     continue
#                 else:
#                     marker_3d_coords.append(marker_3d_coord)
#         return marker_3d_coords
    
def get_bounding_boxes(marker_corners):
    min_corners = np.min(marker_corners, axis=1)
    max_corners = np.max(marker_corners, axis=1)
    
    #!assuming that 0,0 is in the top left
    return [BoundingBox.from_points(top_left=min_corner, bottom_right=max_corner) \
        for min_corner, max_corner in zip(min_corners, max_corners)]
        
    