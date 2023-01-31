import math
import collections
from time import time as now
from enum import Enum

import numpy as np
from super_map import LazyDict
from statistics import mean as average

from pyrealsense2 import rs2_project_color_pixel_to_depth_pixel

from toolbox.globals import path_to, config, print, runtime, time_synchronized
from toolbox.geometry_tools import Position, BoundingBox
from subsystems.aiming.predictor import Predictor
import subsystems.video_stream as video_stream

class TARGET_STATUS(Enum):
    TARGET_NONE = 0
    TARGET_FOUND = 1
    TARGET_ENGAGE = 2

# 
# config
# 
MIN_RANGE                            = config.aiming.min_range
MAX_RANGE                            = config.aiming.max_range
CAMERA                               = config.hardware.camera
DEPTH_COMPATIBLE                     = CAMERA == 'realsense' or CAMERA == 'zed'

# 
# shared data (imported by modeling and integration)
# 
runtime.aiming = LazyDict(
    target_status = TARGET_STATUS.TARGET_NONE,
    target_3d = (0, 0, 0),
    center_point = Position((0, 0)),
)

# 
# main
# 
def when_bounding_boxes_refresh():
    found_robot       = runtime.modeling.found_robot
    best_bounding_box = runtime.modeling.best_bounding_box
    acceleration      = runtime.realsense.acceleration if CAMERA == 'realsense' else None
    gyro              = runtime.realsense.gyro         if CAMERA == 'realsense' else None

    # t1 = time_synchronized()
    # Reset target info at beginning of loop
    center_point = Position((0, 0))
    target_3d = (0, 0, 0)
    target_status = TARGET_STATUS.TARGET_NONE

    # 
    # update core aiming data
    # 
    if found_robot:
        if DEPTH_COMPATIBLE:
            target_3d = get_xyz_at_color_coords([best_bounding_box.center[0].item(), best_bounding_box.center[1].item()])
            # print(f"\ntarget_3d: {target_3d}")
        target_status = TARGET_STATUS.TARGET_FOUND
        
        center_point = Position(best_bounding_box.center) # for displaying

    # update the shared data
    runtime.aiming.target_status      = target_status
    runtime.aiming.target_3d          = target_3d
    runtime.aiming.center_point       = center_point

# 
# helpers
# 
def get_xyz_at_color_coords(point):
    # point is [x, y], return tuple (x, y, z)
    point_3d = video_stream.vid_source.get_xyz_at_point(point)
    point_3d[1], point_3d[2] = point_3d[2], -point_3d[1]
    # X is right/left, Y is forward/backward, Z is up/down
    return point_3d

def get_dist_to_bbox(bbox):
    depth_sample_coords = get_depth_sample_coords(bbox)
    depth_sample = np.array([video_stream.vid_source.get_depth_at_point(point) for point in depth_sample_coords])
    depth_sample = depth_sample[depth_sample > 0]
    if len(depth_sample) == 0:
        return 0
    return np.median(depth_sample)

def get_depth_sample_coords(bbox):
    bbxtl = bbox.x_top_left.item()
    bbytl = bbox.y_top_left.item()
    x, y = np.meshgrid(np.linspace(bbxtl, 
                                   bbxtl + bbox.width.item(),
                                   num=3,
                                   endpoint=True).astype(int),
                       np.linspace(bbytl, 
                                   bbytl + bbox.height.item(),
                                   num=3,
                                   endpoint=True).astype(int))
    return np.stack((x.flatten(), y.flatten()), axis=1)

def distance(point_1: tuple, point_2: tuple):
    """
    Returns the distance between two points.

    Input: Two points.
    Output: Distance in pixels.
    """
    distance = (sum((p1 - p2)*(p1 - p2) for p1, p2 in zip(point_1, point_2))) ** (1 / 2)
    return distance

def angle_from_center(point_to_aim_at, screen_center, horizontal_fov, vertical_fov):
    """
    Returns the x and y angles between the screen_center of the image and the screen_center of a bounding box.

    We send screen_center instead of importing 
    from info.yaml since recorded video footage could be different resolutions.

    Input: Bounding box and camera screen_center.
    Output: Horizontal and vertical angle in radians.
    """

    x_bbox_center, y_bbox_center, x_cam_center, y_cam_center = point_to_aim_at[0], screen_center[1]*2-point_to_aim_at[1], screen_center[0], screen_center[1]

    horizontal_angle = ((x_bbox_center-x_cam_center)/x_cam_center)*(horizontal_fov/2)
    vertical_angle = ((y_bbox_center-y_cam_center)/y_cam_center)*(vertical_fov/2)

    # print("horizontal_angle:",f"{horizontal_angle:.4f}"," vertical_angle:", f"{vertical_angle:.4f}", end=", ")

    return math.radians(horizontal_angle),math.radians(vertical_angle)
