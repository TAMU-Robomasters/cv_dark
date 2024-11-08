# library imports
import numpy as np
import cv2
import os
import time
from super_map import LazyDict

from math import dist, sqrt

# project imports
from toolbox.globals import path_to, config, print, runtime
from toolbox.geometry_tools import BoundingBox, Position
from toolbox.image_tools import Image
import subsystems.aim as aiming

# 
# config
# 
our_team_color        = config.our_team_color
hardware_acceleration = config.model.hardware_acceleration
input_dimension       = config.model.input_dimension
which_model           = config.model.which_model

# config check
assert hardware_acceleration in ['tensor_rt', 'gpu', 'cpu',]

# 
# shared data (imported by aiming and integration)
# 
runtime.modeling = LazyDict(
    bounding_boxes=[],
    enemy_boxes=[],
    confidences=[]
)

# 
# 
# load model
# 
# 
model = LazyDict(
    W=None,
    H=None,
)

if which_model == 'yolo_v4':
    from subsystems.modeling.yolo_v4 import init_yolo_v4
    init_yolo_v4(model)
elif which_model == 'yolo_v5':
    from subsystems.modeling.yolo_v5 import init_yolo_v5
    init_yolo_v5(model)
elif which_model == 'yolo_v7':
    from subsystems.modeling.yolo_v7 import init_yolo_v7
    init_yolo_v7(model)
elif which_model == 'yolo_v8':
    from subsystems.modeling.yolo_v8 import init_yolo_v8
    init_yolo_v8(model)
else:
    raise Exception("Model specified under /'model.which_model/' is not supported")

np.seterr(all='raise')

# 
# 
# main function
# 
# 
def when_frame_arrives():
    frame = runtime.color_image
    
    # 
    # all boxes
    # 
    all_boxes, confidences, class_ids = model.get_bounding_boxes(
        frame=frame,
        minimum_confidence=config.model.minimum_confidence,
    )
    
    screen_center = compute_screen_center(frame)
    # print("Screen center: " + str(screen_center))
    # 
    # remove our team
    # 
    if config.filter_team_color:
        enemy_boxes, confidences, class_ids = filter_plate_color(all_boxes, confidences, class_ids, our_team_color)
    
    # export data
    runtime.screen_center               = screen_center
    runtime.modeling.bounding_boxes     = all_boxes
    runtime.modeling.enemy_boxes        = enemy_boxes
    runtime.modeling.confidences        = confidences

# 
# 
# helpers
# 
# 

if which_model == 'yolo_v5':
    color_to_class_id = dict(
        blue=0,
        red=1,
    )
else:
    color_to_class_id = dict(
        red=0,
        blue=1,
    )

def filter_plate_color(boxes, confidences, class_ids, color_to_remove):
    """
    Filter bounding boxes based on team color.

    Input: Zipped model result of boxes, confidences, and class_ids
    Output: Filtered boxes, confidences, and class_ids
    """
    filtered_boxes = []
    filtered_confidences = []
    filtered_class_ids = []

    # only do this if there are boxes
    if boxes:
        filtered_data = [(box, conf, class_id) for box, conf, class_id in zip(boxes, confidences, class_ids) if class_id == color_to_class_id[color_to_remove]]
        # only unzip if there are boxes left after filtering
        if filtered_data:
            filtered_boxes, filtered_confidences, filtered_class_ids = zip(*filtered_data)
    return filtered_boxes, filtered_confidences, filtered_class_ids

def compute_screen_center(color_image):
    # print("Color image shape: " + str(color_image.shape))
    return (color_image.shape[1] // 2, color_image.shape[0] // 2)