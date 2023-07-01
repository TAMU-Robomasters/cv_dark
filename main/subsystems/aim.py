import math
import collections
from time import time, perf_counter
from enum import Enum

import numpy as np
from super_map import LazyDict
from statistics import mean as average

from toolbox.globals import path_to, config, print, runtime, time_synchronized
from toolbox.geometry_tools import Position, BoundingBox
from subsystems.aiming.predictor import Predictor
from subsystems.video_stream import video_stream

class TargetStatus(Enum):
    TARGET_NONE = 0
    TARGET_FOUND = 1
    TARGET_ENGAGE = 2

# 
# config
# 
MIN_RANGE           = config.aiming.min_range
MAX_RANGE           = config.aiming.max_range
CAMERA              = config.hardware.camera
DEPTH_COMPATIBLE    = config.hardware.camera_has_depth
POSE_COMPATIBLE     = config.hardware.camera_has_pose

# 
# shared data (imported by modeling and integration)
# 
runtime.aiming = LazyDict(
    target_status = TargetStatus.TARGET_NONE,
    target_3d = (0, 0, 0),
    center_point = Position((0, 0)),
)

# 
# main
# 
def when_bounding_boxes_refresh():
    found_robot       = runtime.modeling.found_robot
    best_bounding_box = runtime.modeling.best_bounding_box
    acceleration      = runtime.camera.acceleration if config.hardware.camera_has_acceleration else None
    gyro              = runtime.camera.gyro         if config.hardware.camera_has_gyro         else None

    # Reset target info at beginning of loop
    center_point = Position((0, 0))
    target_3d = (0, 0, 0)
    target_status = TargetStatus.TARGET_NONE

    # 
    # update core aiming data
    # 
    if found_robot:
        if DEPTH_COMPATIBLE:
            sampled_depth = get_dist_to_bbox(best_bounding_box)
            if sampled_depth is None:
                target_status = TargetStatus.TARGET_NONE
            else:
                target_3d = get_xyz_at_color_coords([best_bounding_box.center[0].item(), best_bounding_box.center[1].item()], sampled_depth)
                print(f"\ntarget_3d: {target_3d}")
                # target_3d = get_xyz_at_color_coords([best_bounding_box.center[0].item(), best_bounding_box.center[1].item()])
                if target_3d is None:
                    target_status = TargetStatus.TARGET_NONE
                else:
                    target_status = TargetStatus.TARGET_FOUND
        else:
            target_status = TargetStatus.TARGET_FOUND
        
        # if target_3d[1] < 0:
        #     quit()
        center_point = Position(best_bounding_box.center) # for logging/displays

    # update the shared data
    runtime.aiming.target_status      = target_status
    runtime.aiming.target_3d          = target_3d
    runtime.aiming.center_point       = center_point
    


# 
# helpers
# 
def get_xyz_at_color_coords(point, depth=None):
    # point is [x, y], return tuple (x, y, z)
    point_3d = video_stream.get_xyz_at_color_point(point, depth=depth)
    return point_3d

def get_dist_to_bbox(bbox):
    depth_sample_coords = get_depth_sample_coords(bbox, points_per_dimension=3, width_coverage=0.5, height_coverage=0.5)
    depth_sample = np.array([video_stream.get_depth_at_point(point) for point in depth_sample_coords])
    if depth_sample.shape[0] == 0:
        return None
    depth_sample = depth_sample[depth_sample != None]
    if depth_sample.shape[0] == 0:
        return None
    depth_sample = depth_sample[depth_sample != 0]
    if depth_sample.shape[0] == 0:
        return None
    aim_start = perf_counter()
    depth_sample = reject_depth_outliers(depth_sample)
    aim_end = perf_counter()
    if depth_sample.shape[0] == 0:
        return None
    # print(f"depth_sample: {depth_sample}")
    print(f"Took: {(aim_end - aim_start)*1000} ms")
    # if np.mean(depth_sample) > 5 or np.mean(depth_sample) < 0:
    #     quit()
    return np.mean(depth_sample)

def reject_depth_outliers(depth_sample):
    ''' Use median absolute deviation to reject outliers in depth sample '''
    median = np.median(depth_sample)
    mad = np.median(np.abs(depth_sample - median))
    return depth_sample[np.abs(depth_sample - median) < 3 * mad]

def get_depth_sample_coords(bbox, points_per_dimension=3, width_coverage=0.25, height_coverage=0.25):
    bbox_width_coverage = bbox.width.item() * width_coverage
    bbox_height_coverage = bbox.height.item() * height_coverage

    bbxtl = max(bbox.center[0].item() - (bbox_width_coverage // 2), 0)
    bbytl = max(bbox.center[1].item() - (bbox_height_coverage // 2), 0)

    bbxbr = min(bbxtl + bbox_width_coverage, runtime.color_image.shape[1] - 1)
    bbybr = min(bbytl + bbox_height_coverage, runtime.color_image.shape[0] - 1)

    x_range = (bbxbr - bbxtl) // (points_per_dimension - 1) if points_per_dimension > 1 else bbxbr - bbxtl
    y_range = (bbybr - bbytl) // (points_per_dimension - 1) if points_per_dimension > 1 else bbybr - bbytl

    coords = []
    for i in range(points_per_dimension):
        for j in range(points_per_dimension):
            x = int(bbxtl + x_range * i)
            y = int(bbytl + y_range * j)
            coords.append([x, y])
    return np.array(coords)