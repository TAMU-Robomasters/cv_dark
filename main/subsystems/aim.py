import math
import collections
from time import time as now
from enum import Enum

import numpy as np
from super_map import LazyDict
from statistics import mean as average

from toolbox.globals import path_to, config, print, runtime, time_synchronized
from toolbox.geometry_tools import Position, BoundingBox
from subsystems.aiming.predictor import Predictor
import subsystems.video_stream as video_stream

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
            # if sampled_depth is None:
            #     target_status = TargetStatus.TARGET_NONE
            # else:
            target_3d = get_xyz_at_color_coords([best_bounding_box.center[0].item(), best_bounding_box.center[1].item()], sampled_depth)
            # target_3d = get_xyz_at_color_coords([best_bounding_box.center[0].item(), best_bounding_box.center[1].item()])
            print(f"\ntarget_3d: {target_3d}")
            if target_3d is not None:
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
    point_3d = video_stream.vid_source.get_xyz_at_color_point(point, depth=depth)
    return point_3d

def get_dist_to_bbox(bbox):
    depth_sample_coords = get_depth_sample_coords(bbox, points_per_dimension=3, width_coverage=0.5, height_coverage=0.5)
    depth_sample = np.array(
        [video_stream.vid_source.get_depth_at_point(point) for point in depth_sample_coords]
    )
    depth_sample = depth_sample[depth_sample != None]
    depth_sample = depth_sample[depth_sample != 0]
    depth_sample = reject_depth_outliers(depth_sample)
    print(f"depth_sample: {depth_sample}")
    if len(depth_sample) == 0:
        return None
    # if np.mean(depth_sample) > 5 or np.mean(depth_sample) < 0:
    #     quit()
    return np.mean(depth_sample)

def reject_depth_outliers(depth_sample):
    ''' Use median absolute deviation to reject outliers in depth sample '''
    median = np.median(depth_sample)
    mad = np.median(np.abs(depth_sample - median))
    return depth_sample[np.abs(depth_sample - median) < 3 * mad]

def get_depth_sample_coords(bbox, points_per_dimension=3, width_coverage=0.5, height_coverage=0.5):
    bbox_width_coverage = bbox.width.item() * width_coverage
    bbox_height_coverage = bbox.height.item() * height_coverage

    bbxtl = bbox.center[0].item() - (bbox_width_coverage / 2)
    bbytl = bbox.center[1].item() - (bbox_height_coverage / 2)

    x, y = np.meshgrid(
        np.linspace(
            bbxtl,
            bbxtl + bbox_width_coverage,
            num=points_per_dimension,
            endpoint=True
        ).astype(int),
        np.linspace(
            bbytl,
            bbytl + bbox_height_coverage,
            num=points_per_dimension,
            endpoint=True
        ).astype(int),
    )
    return np.stack((x.flatten(), y.flatten()), axis=1)
