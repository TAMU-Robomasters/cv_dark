from toolbox.globals import runtime, config
from toolbox.geometry_tools import BoundingBox, Position
import numpy as np
import cv2
from subsystems.aim import get_dist_to_bbox, get_xyz_at_color_coords
from enum import Enum
# import frame
R_FRAME = runtime.color_image

class TargetStatus(Enum):
    TARGET_NONE = 0
    TARGET_FOUND = 1
    TARGET_ENGAGE = 2

def paper_detector():
    
    # your algorithm should output a top left corner and bottom right corner
    # then we use these to corners to instantiate a BoundingBox object
    frame = R_FRAME
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    lower_blue = np.array([40, 100, 100])
    upper_blue = np.array([80, 255, 255])

    mask = cv2.inRange(hsv, lower_blue, upper_blue)


    result = cv2.bitwise_and(frame, frame, mask=mask)

    #cv2.imshow('Original', frame)
    #cv2.imshow('Mask', mask)
    #cv2.imshow('Filtered', result)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    max_w = 0
    max_h = 0
    x, y, w, h = 0, 0, 0, 0
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if (w > max_w):
            max_w = w
        if (h > max_h):
            max_h = h
    #cv2.rectangle(frame, (x, y), (x + max_w, y + max_h), (0, 255, 0), 2) # Draw the rectangle on the original image
    #cv2.rectangle(result, (x, y), (x + max_w, y + max_h), (0, 255, 0), 2) # Draw the rectangle on the original image
    cv2.rectangle(result, (x, y), (x + max_w, y + max_h), (0, 255, 0), 2) # Draw the rectangle on the original image

    # Parameters for circle
    #center = (x + (max_w / 2), y + (max_h / 2))
    circle_x = int(x + max_w / 2)
    circle_y = int(y + max_h / 2)
    center = (circle_x, circle_y)
    box = BoundingBox.from_points(top_left=(x, y), bottom_right=(x + max_w, y + max_h))
    sampled_depth = get_dist_to_bbox(box)
    target_3d_coord = get_xyz_at_color_coords([circle_x, circle_y], sampled_depth)

    radius = 5
    color = (0, 255, 0)
    thickness = 2
    result = cv2.circle(result, center, radius, color, thickness)
    #cv2.imshow('Original', frame)
    #cv2.imshow('Mask', mask)
    cv2.imshow('Filtered', result)

    
    # export bbox
    center = Position(circle_x, circle_y)
    target_status = TargetStatus.TARGET_FOUND
    if (x == 0 and y == 0 and w == 0 and h == 0):
        target_status = TargetStatus.TARGET_NONE
    runtime.modeling.bounding_box = box
    runtime.aiming.target_status      = target_status
    runtime.aiming.target_3d          = target_3d_coord
    runtime.aiming.center_point       = center
    runtime.modeling.found_robot        = box is not None
    