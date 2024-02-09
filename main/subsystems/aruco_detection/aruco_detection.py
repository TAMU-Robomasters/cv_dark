# add new markers

import math
from time import time_ns

import cv2 as cv
import numpy as np
import pyrealsense2 as rs
from cv2 import aruco
from super_map import LazyDict
from toolbox.globals import runtime

from kalman_class import KalmanFilter2D

# Shared memory. Idea here is parallel arrays for each field of the aruco detection
runtime.aruco_detection = LazyDict(
    rel_x=[],
    rel_y=[],
    color=[],
    letter=[],
)

# These patterns are the A/B/C/D/E markers that we see on the field.
a_pattern = np.array([
    [0, 0, 1, 0, 0],
    [0, 1, 0, 1, 0],
    [1, 1, 1, 1, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1], ], dtype=np.uint8)

b_pattern = np.array([
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 0], ], dtype=np.uint8)

c_pattern = np.array([
    [0, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 0],
    [1, 0, 0, 0, 1],
    [0, 1, 1, 1, 0], ], dtype=np.uint8)

d_pattern = np.array([
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 0], ], dtype=np.uint8)

e_pattern = np.array([
    [1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0],
    [1, 1, 1, 1, 0],
    [1, 0, 0, 0, 0],
    [1, 1, 1, 1, 1], ], dtype=np.uint8)

# create a dict of id to letter
id_to_letter = {
    0: 'a',
    1: 'b',
    2: 'c',
    3: 'd',
    4: 'e'
}


def add_marker(aruco_dict, marker_name, marker_pattern):
    aruco_dict.bytesList[marker_name] = aruco.Dictionary_getByteListFromBits(marker_pattern)


# Checks if a matrix is a valid rotation matrix.
def is_rotation_matrix(R):
    Rt = np.transpose(R)
    shouldBeIdentity = np.dot(Rt, R)
    I = np.identity(3, dtype=R.dtype)
    n = np.linalg.norm(I - shouldBeIdentity)
    return n < 1e-6


# Calculates rotation matrix to euler angles
# The result is the same as MATLAB except the order
# of the euler angles ( x and z are swapped ).
def rotation_matrix_to_euler_angles(R):
    assert (is_rotation_matrix(R))

    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])

    singular = sy < 1e-6

    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0

    return np.array([x, y, z])


# Initialize an empty list to store moving averages
USING_REALSENSE = True

if USING_REALSENSE:
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 1920, 1080, rs.format.bgr8, 30)  # Configuring color stream

else:
    stream = cv.VideoCapture(0)

calib_data_path = "CalMatrix.npz"

calib_data = np.load(calib_data_path)

cam_mat = calib_data["camMatrix"]
dist_coef = calib_data["distCoef"]

MARKER_SIZE = 15

# define an empty custom dictionary with
aruco_dict = aruco.Dictionary(6, 5, 0)
# add empty bytesList array to fill with 3 markers later
aruco_dict.bytesList = np.empty(shape=(5, 4, 4), dtype=np.uint8)

parameters = cv.aruco.DetectorParameters()
detector = cv.aruco.ArucoDetector(aruco_dict, parameters)

add_marker(aruco_dict, 0, a_pattern)
add_marker(aruco_dict, 1, b_pattern)
add_marker(aruco_dict, 2, c_pattern)
add_marker(aruco_dict, 3, d_pattern)
add_marker(aruco_dict, 4, e_pattern)

# Kalman filter init

# Define the Kalman filter parameters
initial_state = np.array([0, 0, 0, 0, 0, 0])  # Initial position and velocity in x and y
initial_covariance = np.eye(6) * 100000  # Initial covariance matrix
process_noise = 1e-3  # Process noise
measurement_noise = .01  # Measurement noise

kalman_filter = KalmanFilter2D(initial_state, initial_covariance, process_noise, measurement_noise)
past_time = time_ns() / 1e9  # Get current time in seconds
current_time = 0


def when_detection_refreshes():
    global field, kalman_filter, past_time, current_time
    frame = runtime.color_frame
    # Convert RealSense frame to OpenCV format
    # TODO: DETERMINE IF FRAME IS IN PROPER FORMAT FOR USAGE. THIS WILL NEED TO BE TESTED ON THE JETSON.
    # frame = np.asanyarray(color_frame.get_data())

    field = np.zeros((800, 1200, 3))

    if frame.size > 2:
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
        marker_corners, marker_IDs, reject = aruco.detectMarkers(gray_frame, aruco_dict)
    if marker_corners:
        rVec, tVec, _ = aruco.estimatePoseSingleMarkers(marker_corners, MARKER_SIZE, cam_mat, dist_coef)

        total_markers = range(0, marker_IDs.size)  # TODO: @JaiPatel: Will this return the detections for multiple aruco markers? I don't think so. That stuff should be inside the for loop
        for ids, corners, i in zip(marker_IDs, marker_corners, total_markers):
            corners = corners.reshape(4, 2).astype(np.int32)

            # Create a mask for the parallelogram region
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)

            # Compute the mean color within the masked region
            mean_color = cv.mean(frame, mask=mask)[:3]

            detected_color = "N/A"
            if mean_color[0] > 125:
                detected_color = "Blue"
            elif mean_color[2] > 125:
                detected_color = "Red"

            detected_letter = id_to_letter[ids[0]].upper()

        rVec = rVec[0][0]
        tVec = tVec[0][0]

        rVec_flipped = rVec * -1
        tVec_flipped = tVec * -1
        rotation_matrix, jacobian = cv.Rodrigues(rVec_flipped)
        realworld_tVec = np.dot(rotation_matrix, tVec_flipped)

        # TODO: not sure if embedded wants deez
        # pitch, roll, yaw = rotation_matrix_to_euler_angles(rotation_matrix)

        robot_cord = [int(490 - realworld_tVec[2]), int(800 - (305 + 100) + realworld_tVec[0])]

        measurement = np.array([robot_cord[0], robot_cord[1]])  # Example measurement function
        current_time = time_ns() / 1e9  # Get current time in seconds
        kalman_filter.predict(dt=current_time - past_time)
        past_time = current_time
        kalman_filter.update(measurement)
        filtered_x = kalman_filter.state[0]
        filtered_y = kalman_filter.state[1]  # Extract filtered x and y positions

        # Save the filtered x and y positions to the shared data with color and letter
        runtime.aruco_detection.rel_x.append(filtered_x)
        runtime.aruco_detection.rel_y.append(filtered_y)
        runtime.aruco_detection.color.append(detected_color)
        runtime.aruco_detection.letter.append(detected_letter)
