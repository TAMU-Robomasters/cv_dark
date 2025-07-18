# library imports
import cv2
import math
import numpy as np
from super_map import LazyDict

# project imports
from toolbox.globals import path_to, config, print, runtime
from toolbox.geometry_tools import BoundingBox, Position

ARMOR_HEIGHT_RATIO = 12.5/5.2
ARMOR_WIDTH_RATION = 5.5/13

class Lights:
    def __init__(self, cx, cy, w, h, angle):
        self.cx = cx
        self.cy = cy
        self.w = w
        self.h = h
        self.angle = angle

# 
# config
# 
ENEMY_COLOR       = config.our_team_color


# 
# shared data (imported by aiming and integration)
# 
runtime.modeling = LazyDict(
    bounding_boxes=[],
    enemy_boxes=[],
    confidences=[],
    best_bounding_box=[],
    current_confidence=0,
    found_robot=False,
)

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
    enemy_boxes = get_enemy_bounding_boxes(frame)
    
    screen_center = (frame.shape[1] // 2, frame.shape[0] // 2)
    # print("Screen center: " + str(screen_center))


    # export data
    runtime.screen_center               = screen_center
    runtime.modeling.bounding_boxes     = enemy_boxes
    runtime.modeling.enemy_boxes        = enemy_boxes
    # runtime.modeling.confidences        = confidences
    # runtime.modeling.best_bounding_box  = best_bounding_box
    # runtime.modeling.current_confidence = current_confidence
    # runtime.modeling.found_robot        = best_bounding_box is not None



#
#
# helpers
#
#
color_to_class_id = dict(
    red=0,
    blue=1,
)
def get_enemy_bounding_boxes(frame):
    contours = get_contours(frame)
    lights = get_lights(contours)
    if len(lights) > 1:
        pairs = pairing(lights)
        panels = []
        for pair in pairs:
            corners = armour_corners(pair)
            panels.append(corners)
    
    bounding_boxes_corners = [cv2.boundingRect(panel) for panel in panels] # returns tuple of bottom left and top right points
    bounding_boxes = [BoundingBox.from_points(top_left=(corners[0],corners[3]), bottom_right=(corners[2],corners[1])) for corners in bounding_boxes_corners]
    return bounding_boxes
    

def get_contours(frame):
    """
    function will split color channels, threshold, and find contours.
    :param frame: input frame
    :param enemy_color: color of the enemy
    :return: contours
    """

    if (ENEMY_COLOR == 'BLUE'):
        _, thresh = cv2.threshold(frame[:,:,0], 215, 240, cv2.THRESH_BINARY) # tune before match
    elif (ENEMY_COLOR == 'RED'):
        _, thresh = cv2.threshold(frame[:,:,2], 215, 240, cv2.THRESH_BINARY) # tune before match
    else:
        print('invalid color')

    kernel = np.ones((3,3),np.uint8)
    closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closing, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    return contours


def get_lights(contours):
    """
    creating bounding boxes around lights
    :param frame:
    :param contours:
    :return: list of bounding boxes
    """
    b_boxes = []
    for contour in contours:# have to keep
        rect = cv2.minAreaRect(contour)
        h_holder, w_holder = rect[1]

        if rect[1][0] > rect[1][1]:
            h,w = rect[1]
        else:
            w,h = rect[1]

        angle = rect[2]
        if w_holder > h_holder:
            angle += 90

        # filter out bad detections: true if bad
        if ((abs(angle-90) > 45)):
            continue
        else:
            b_box = Lights(rect[0][0], rect[0][1], w, h, angle)
            b_boxes.append(b_box)

    return b_boxes

def pairing(b_boxes):
    """
    Pairs lights together based off of similarity score using vectorized operations
    
    :param b_boxes: List of light objects to be paired
    :return: list of pairs of lights
    """
    n = len(b_boxes)
    if n <= 1:
        return []

    # Convert light objects to structured array in one go
    light_data = np.array([(light.cx, light.cy, light.angle, light.h) 
                          for light in b_boxes],
                         dtype=[('cx', 'f8'), ('cy', 'f8'), 
                               ('angle', 'f8'), ('h', 'f8')])

    # Extract arrays using structured array fields
    cx = light_data['cx']
    cy = light_data['cy']
    angles = light_data['angle']
    heights = light_data['h']

    # Create meshgrids for vectorized calculations
    cx1, cx2 = np.meshgrid(cx, cx)
    cy1, cy2 = np.meshgrid(cy, cy)
    angles1, angles2 = np.meshgrid(angles, angles)
    heights1, heights2 = np.meshgrid(heights, heights)

    # Calculate all metrics at once
    dx = cx1 - cx2
    dy = cy1 - cy2
    distances = np.hypot(dx, dy)
    angle_diffs = np.abs(angles1 - angles2)
    misalignment_angles = np.abs(np.degrees(np.arctan2(dy, dx)))
    height_ratios = heights1 / heights2
    avg_heights = (heights1 + heights2) / 2
    expected_distances = np.abs((avg_heights / ARMOR_WIDTH_RATION) - distances)

    # Calculate scores
    scores = angle_diffs + 1.25 * misalignment_angles + expected_distances*0.5 + height_ratios

    # Create mask for valid pairs
    valid_mask = (
        (angle_diffs < 45) &  # Angle difference threshold
        (misalignment_angles < 30) &  # Misalignment threshold
        (height_ratios > 0.5) & (height_ratios < 2.0) &  # Height ratio threshold
        (scores < 50)  # Score threshold
    )

    # Set invalid pairs (same light) to infinite score
    np.fill_diagonal(scores, np.inf)

    pairs = []
    used = set()

    # Get pairs in order of increasing score
    while True:
        # Find minimum score indices
        min_idx = np.unravel_index(scores.argmin(), scores.shape)
        min_score = scores[min_idx]
        
        if min_score == np.inf or not valid_mask[min_idx]:
            break

        i, j = min_idx
        if i not in used and j not in used:
            pairs.append([b_boxes[i], b_boxes[j]])
            used.add(i)
            used.add(j)

        # Mark this pair as used by setting its score to infinity
        scores[i, j] = scores[j, i] = np.inf

    return pairs

def armour_corners(pair):
    """
    an absolute monster of math. 
    :param pairs: list of pairs
    :param frame:
    :return: list of 4 points
    """
    # Since pair is a list of two Lights objects
    light1, light2 = pair[0], pair[1]
    # Determine left and right lights based on x-coordinate
    if light1.cx <= light2.cx:
        left = light1
        right = light2
    else:
        left = light2
        right = light1

    top_left = [int(left.cx + left.w * 0.5 - (left.h * ARMOR_HEIGHT_RATIO) * 0.5 * math.cos(
        math.radians(left.angle))), int((left.cy - (
                (left.h * ARMOR_HEIGHT_RATIO) * 0.5 * math.sin(math.radians(left.angle)))))]
    top_right = [int(right.cx - right.w * 0.5 - (right.h * ARMOR_HEIGHT_RATIO) * 0.5 * math.cos(
        math.radians(right.angle))), int((right.cy - (
                (right.h * ARMOR_HEIGHT_RATIO) * 0.5 * math.sin(math.radians(right.angle)))))]
    bottom_left = [int(left.cx + left.w * 0.5 + (left.h * ARMOR_HEIGHT_RATIO) * 0.5 * math.cos(
        math.radians(left.angle))), int((left.cy + (
                (left.h * ARMOR_HEIGHT_RATIO) * 0.5 * math.sin(math.radians(left.angle)))))]
    bottom_right = [int(
        right.cx - right.w * 0.5 + (right.h * ARMOR_HEIGHT_RATIO) * 0.5 * math.cos(
            math.radians(right.angle))), int((right.cy + (
                (right.h * ARMOR_HEIGHT_RATIO) * 0.5 * math.sin(math.radians(right.angle)))))]

    points = np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.int32)
    points = points.reshape((-1, 1, 2))
    
    return  points