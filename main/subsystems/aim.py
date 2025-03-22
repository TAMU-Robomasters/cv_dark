from math import dist, exp
import collections
import numpy as np
import time
from time import perf_counter
from enum import Enum

import numpy as np
from super_map import LazyDict

from toolbox.globals import config, print, runtime
from toolbox.geometry_tools import Position
# NOTE change in the future
from toolbox.kalman_filter import KF2D, KF3D
from subsystems.video_stream import video_stream

class TargetStatus(Enum):
    TARGET_NONE = 0
    TARGET_FOUND = 1

kf_2d = KF2D(np.ones((6,1), dtype=np.float32), 0.1, 0.1, 0.05, 0.05)
kf_3d = KF3D(np.ones((9,1), dtype=np.float32), 1.0, 0.0, 0.01, 0.05, 0.2)


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
#? is the lazy dict necessary?
runtime.aiming = LazyDict(
    target_status = TargetStatus.TARGET_NONE,
    target_3d = Position((0, 0, 0)),
    center_point = Position((0, 0)),
    best_bounding_box=[],
    current_confidence=0,
    storedPrediction = [(0,0,0),(0,0,0)]
)

#TODO find a cleaner way of doing this
past_time = time.time()  # get time in seconds

# 
# main
# 
def when_bounding_boxes_refresh():
    global past_time #? is there a better way
    enemy_boxes             = runtime.modeling.enemy_boxes 
    enemy_confidences       = runtime.modeling.confidences 
    screen_center           = runtime.screen_center
    # Reset variables at beginning of loop
    center_point            = Position((0, 0))
    center_point_prediction = Position((0, 0))
    target_3d_prediction    = Position((0, 0, 0))

    validBoxes          = []
    validConfidences    = []
    valid3dTargets      = []

    best_bounding_box   = None
    current_confidence  = 0
    best_target_3d      = Position((0,0,0))

    # 
    # update core aiming data
    #

    # filter list of boxes/confidences that are valid before finding the best one
    if DEPTH_COMPATIBLE:
        for box,confidence in zip(enemy_boxes,enemy_confidences):
            sampled_depth = get_dist_to_bbox(box)
            if sampled_depth is None:
                continue
            elif sampled_depth < MIN_RANGE or sampled_depth > MAX_RANGE:
                continue
            else:
                target_3d = get_xyz_at_color_coords([box.center[0].item(), box.center[1].item()], sampled_depth)
                # print(f"\ntarget_3d: {target_3d}")
                if target_3d is None:
                    continue
                else:
                    validBoxes.append(box)
                    validConfidences.append(confidence)
                    valid3dTargets.append(target_3d)
        if (validBoxes != []):
            # now that we have the valid boxes lets compute the best ones as 3d targets
            best_bounding_box, current_confidence, best_target_3d  = get_optimal_3d_target(
                boxes = validBoxes, 
                confidences = validConfidences,
                screen_center = screen_center,
                valid3dTargets = valid3dTargets,
            )
        if (best_bounding_box != None):
            center_point = Position(best_bounding_box.center) # for logging/displays

            curr_time = time.time()
            """!TODO Fix bug: during the first iteration of the kalman filter the 
            velocity and acceleration could be really high if there's no target found
            with a short period of time."""
            time_since_last_measurement = curr_time - past_time # in seconds

            measurement = np.array(best_target_3d, dtype=np.float32)
            kf_3d.predict(time_since_last_measurement)
            kf_3d.correct(measurement) 
            past_time = time.time()

            try:
                frame_delay = (time.time() - video_stream.capture_time / 1E3) # seconds
            except AttributeError:
                print(f"Warning current camera:{CAMERA} does not have capture time attribute in its VideoStream class")
                frame_delay = time_since_last_measurement
            if frame_delay > 0.255:
                print(f"Warming frame delay of {frame_delay} is really high")
            # this contains the prediction of all the state variables [x, vx, ax, y, vy, ay, z, vz, az]
            forward_prediction = kf_3d.forward_predict(frame_delay) 
            target_3d_prediction = Position((forward_prediction[0], forward_prediction[3], forward_prediction[6]))
            runtime.aiming.storedPrediction.append(best_target_3d)
    else:
        # if camera is not depth capable, find best box
        # mostly used for testing purposes
        best_bounding_box, current_confidence = get_best_bounding_box(
            boxes = enemy_boxes,
            confidences = enemy_confidences,
            screen_center = screen_center
        )
        if (best_bounding_box != None):
            center_point = Position(best_bounding_box.center) # for logging/displays

            # Predict position using Kalman filters4
            curr_time = time.time()
            time_since_last_measurement = curr_time - past_time # in seconds

            # pulling out from GPU only drops the fps by ~3
            center_point.x = int(center_point.x.cpu())
            center_point.y = int(center_point.y.cpu())
            measurement = np.array([center_point.x, center_point.y], dtype=np.float32)
            kf_2d.predict(time_since_last_measurement)
            kf_2d.correct(measurement) 
            past_time = time.time()

            try:
                frame_delay = (time.time() - video_stream.capture_time / 1E3) # seconds
            except AttributeError:
                print(f"Warning current camera:{CAMERA} does not have capture time attribute in its VideoStream class")
                frame_delay = time_since_last_measurement
            if frame_delay > 0.255:
                print(f"Warming frame delay of {frame_delay} is really high")
            # this contains the prediction of all the state variables [x, vx, ax, z, vz, az]
            forward_prediction = kf_2d.forward_predict(frame_delay)
            center_point_prediction = Position((forward_prediction[0], forward_prediction[3]))
            
   
   
    # update the shared data
    runtime.aiming.target_status            = TargetStatus.TARGET_NONE if best_bounding_box is None else TargetStatus.TARGET_FOUND
    runtime.aiming.target_3d                = best_target_3d
    runtime.aiming.center_point             = center_point
    runtime.aiming.center_point_prediction  = center_point_prediction
    runtime.aiming.best_bounding_box        = best_bounding_box
    runtime.aiming.current_confidence       = current_confidence
    runtime.aiming.target_3d_prediction     = target_3d_prediction


# 
# helpers
# 

# Parameter list: target3d list, bounding boxes?, and confidences
# To determine the optimal bounding box to return out of the target list,
# run the get_optimal_bounding_box from model.py but now add target3d
# Metric 1: use depth aka valid3dTargets[1] aka y axis (take closest)
# Metric 2: median xyz point of clustered points (3), 'noise' points weight lower
# Idea - is random boxlist length(1) is FAR from screenCenter
# Temporal, overtime noise rejection
# ------------
# 
def get_optimal_3d_target(boxes, confidences, screen_center, valid3dTargets):
#    """
#     Decide the single best bounding box to aim at using a score system.

#     Input: All detected bounding boxes with their confidences and the screen_center location of the image.
#     Output: Best bounding box and its confidence.
#     """
    # no boxes
    if not boxes:
        return None, 0 , None
    # if len(boxes) == 1:
    #     return boxes[0], confidences[0]

    best_bounding_box = boxes[0]
    best_score = 0
    best_conf = 0
    best_depth = 0
    best_targ_3d = (0,0,0)
    best_circle_bias_score = 0

    screen_center_normalizer = dist((screen_center[0]*2,screen_center[1]*2),(screen_center[0],screen_center[1])) # Find constant used to scale distance part of score to 1
    size_normalizer = 0.7 # plate at closest distance is 0.7 of the screen

    # Sequentially iterate through all bounding boxes
    for conf, box, targetXYZ in zip(confidences, boxes, valid3dTargets):
        size_score = ((box.width / (runtime.color_image.shape[1])) / size_normalizer) # Compute score using size of box, relative to total image size
        # print(f"size_score: {size_score}")
        center_score = (1 - dist(screen_center,(box[0] + box[2]/2, box[1] + box[3]/2)) / screen_center_normalizer) # scaled to 1
        # print(f"center_score: {center_score}")
        conf_score = conf**2 # Compute score using confidence
        # print(f"conf_score: {conf_score}")

        # clamped to 0 to 1
        # this is a 2d point - want to draw a circle
        # radius dependent on the depth? tweak1
        # exponential instead of linear? tweak2
        distance = (dist(runtime.aiming.center_point, Position(box.center)) / 100)
        radius = 100
        if distance >= radius:
            circle_bias_score = 0  # The point is at the edge or outside the circle
        else:
            circle_bias_score = 1 - (distance / radius)  # Calculate the score based on the normalized distance
        # print(f"circle_bias_score: {circle_bias_score}")
        
        # linear appraoch (based on max and min range in info.yaml min and max is 1m to 5m)
        # ex. when targetXYZ[1] is 3.5, 
        # the depth_score is computed as 0.625, which falls within the clamped range of 0 to 1.
        # depth_score = max(0, min(1, (targetXYZ[1] - 1.0) / 4.0))

        # exponential approach 
        # (values closer to 1 will result in higher depth_score values)
        # ex. targetXYZ[1] is 3.5, the depth_score calculated using the exponential approach is approximately 0.2865
        depth_score = max(0, min(MIN_RANGE, exp((1 - targetXYZ[1]) / 2)))
        # print(f"depth_score: {depth_score}")
        # Compute score using weighted average
        # score = 0.625 * size_score + 0.125 * center_score + 0.125 * depth_score + 0.125 * circle_bias_score 
        score = 0.125 * size_score + 0.125 * center_score + 0.125 * depth_score + 0.625 * circle_bias_score 
        score *= conf_score
        # print(f"score: {score}")

        # Make current box the best if its score is the best so far
        if score > best_score:
            best_bounding_box = box
            best_conf = conf
            best_targ_3d = targetXYZ
            best_score = score
    # if best_score < 0.15:
    #     return None, 0
    # if size_score < 5:
    #     return None, 0
    return best_bounding_box, best_conf, best_targ_3d


def get_best_bounding_box(boxes, confidences, screen_center):
    """
    Decide the single best bounding box to aim at using a score system.

    Input: All detected bounding boxes with their confidences and the screen_center location of the image.
    Output: Best bounding box and its confidence.
    """
    # no boxes
    if not boxes:
        return None, 0
    # if len(boxes) == 1:
    #     return boxes[0], confidences[0]

    best_bounding_box = boxes[0]
    best_score = 0
    best_conf = 0

    screen_center_normalizer = dist((screen_center[0]*2,screen_center[1]*2),(screen_center[0],screen_center[1])) # Find constant used to scale distance part of score to 1
    size_normalizer = 0.7 # plate at closest distance is 0.7 of the screen

    # Sequentially iterate through all bounding boxes
    for conf, box in zip(confidences, boxes):
        size_score = ((box.width / (runtime.color_image.shape[1])) / size_normalizer) # Compute score using size of box, relative to total image size
        # print(f"size_score: {size_score}")
        center_score = (1 - dist(screen_center,(box[0] + box[2]/2, box[1] + box[3]/2)) / screen_center_normalizer) # scaled to 1
        # print(f"center_score: {center_score}")
        conf_score = conf**2 # Compute score using confidence
        # print(f"conf_score: {conf_score}")
        score = 0.75 * size_score + 0.125 * center_score + 0.125 * conf_score # Compute score using weighted average
        # print(f"score: {score}")

        # Make current box the best if its score is the best so far
        if score > best_score:
            best_bounding_box = box
            best_conf = conf
            best_score = score
    # if best_score < 0.15:
    #     return None, 0
    # if size_score < 5:
    #     return None, 0
    return best_bounding_box, best_conf


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
    # print(f"Took: {(aim_end - aim_start)*1000} ms")
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
