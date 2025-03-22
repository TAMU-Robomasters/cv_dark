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
# TODO: rebase this to master
from toolbox.kalman_filter import KF2D, KF3D
from subsystems.video_stream import video_stream

class TargetStatus(Enum):
    TARGET_NONE = 0
    TARGET_FOUND = 1


# NOTE initial kinematic state is set to all ones. This might effect convergence time
# TODO find better uncertainty for x, y, z
kf_2d = KF2D(np.ones((6,1), dtype=np.float32), 0.1, 0.1, 0.05, 0.05)
kf_3d = KF3D(np.ones((9,1), dtype=np.float32), 0.1, 0.1, 0.1, 0.05, 0.2)


# DFT implementation for spin detection
class DFTHelper:
    def __init__(self, buffer_size=30, damping_factor=0.999):
        """
        Initialize DFT helper for spin detection
        
        Implements the same approach as in comp/spin-detection for detecting spinning targets.
        
        Args:
            buffer_size: Size of the buffer for DFT calculation
            damping_factor: Damping factor to control sensitivity
        """
        self.buffer_size = buffer_size
        self.damping_factor = damping_factor
        # Initialize buffer with zeros
        self.buffer = np.zeros(buffer_size, dtype=np.float32)
        # Initialize DFT output array
        self.dft = np.zeros(buffer_size, dtype=np.complex64)
        # DFT is not valid until buffer has sufficient non-zero values
        self.is_valid = False
        # Threshold indices for middle frequency range (as in comp/spin-detection)
        self.dft_threshold_1 = buffer_size // 4
        self.dft_threshold_2 = 3 * (buffer_size // 4)
        # Simple filter for smoothing spin magnitude
        self.spin_magnitude_filter = 0.0
        self.spin_filter_alpha = 0.2  # Filter coefficient
        
        # Track dominant frequency and phase for better prediction
        self.dominant_frequency_idx = 0
        self.dominant_phase = 0.0
        self.amplitude = 0.0
        
    def update(self, new_value):
        """
        Update the DFT with a new position value
        
        Args:
            new_value: New position value to add to the buffer
            
        Returns:
            bool: True if DFT is valid, False otherwise
        """
        # Apply damping factor to existing buffer
        self.buffer = self.buffer * self.damping_factor
        # Shift buffer and add new value
        self.buffer = np.roll(self.buffer, -1)
        self.buffer[-1] = new_value
        
        # Calculate DFT
        self.dft = np.fft.fft(self.buffer)
        
        # Find dominant frequency (excluding DC)
        magnitudes = np.abs(self.dft[1:self.buffer_size//2])
        if len(magnitudes) > 0 and np.max(magnitudes) > 0:
            self.dominant_frequency_idx = np.argmax(magnitudes) + 1
            self.dominant_phase = np.angle(self.dft[self.dominant_frequency_idx])
            self.amplitude = magnitudes[self.dominant_frequency_idx - 1]
        
        # DFT is valid after buffer is filled
        if not self.is_valid and np.count_nonzero(self.buffer) >= self.buffer_size//2:
            self.is_valid = True
            
        return self.is_valid
    
    def is_data_valid(self):
        """
        Check if the DFT data is valid
        
        Returns:
            bool: True if DFT is valid, False otherwise
        """
        return self.is_valid
    
    def get_spin_magnitude(self):
        """
        Calculate spin magnitude by analyzing the middle frequency range
        
        This follows the exact approach in comp/spin-detection:
        1. Calculate average magnitude in middle frequency range
        2. Apply a simple filter to smooth the result
        
        Returns:
            float: Filtered spin magnitude
        """
        if not self.is_valid:
            return 0.0
        
        # Calculate average magnitude in the middle frequency range
        magnitude_avg_middle_half = 0.0
        count = 0
        
        for i in range(self.dft_threshold_1, self.dft_threshold_2):
            # Calculate magnitude of complex number
            magnitude = np.abs(self.dft[i])
            magnitude_avg_middle_half += magnitude
            count += 1
            
        # Average the magnitudes
        if count > 0:
            magnitude_avg_middle_half /= count
            
        # Apply simple low-pass filter to smooth the magnitude
        self.spin_magnitude_filter = (self.spin_filter_alpha * magnitude_avg_middle_half + 
                                     (1 - self.spin_filter_alpha) * self.spin_magnitude_filter)
        
        return self.spin_magnitude_filter
    
    def get_dominant_frequency(self):
        """
        Get the dominant frequency index from the DFT
        
        Returns:
            int: Index of dominant frequency
        """
        return self.dominant_frequency_idx
    
    def get_phase(self):
        """
        Get the phase of the dominant frequency
        
        Returns:
            float: Phase in radians
        """
        return self.dominant_phase
    
    def get_amplitude(self):
        """
        Get the amplitude of the dominant frequency
        
        Returns:
            float: Amplitude
        """
        return self.amplitude


# Position filter for removing spin (heavy filtering)
# This is used when spin is detected to get a more stable position
class SpinRemovalFilter:
    def __init__(self, alpha=0.05):
        """
        Simple exponential filter for removing spin from position data
        
        Args:
            alpha: Filter coefficient (0.0-1.0)
                  Lower values provide more filtering (smoother output)
                  Higher values respond faster to changes
        """
        self.filtered_value = 0.0
        self.alpha = alpha
        self.initialized = False
        
    def update(self, new_value):
        """
        Update the filter with a new position value
        
        Args:
            new_value: New position value
            
        Returns:
            float: Filtered position value
        """
        if not self.initialized:
            self.filtered_value = new_value
            self.initialized = True
            return self.filtered_value
            
        # Apply exponential filter: y[n] = α*x[n] + (1-α)*y[n-1]
        self.filtered_value = self.alpha * new_value + (1 - self.alpha) * self.filtered_value
        return self.filtered_value
    
    def set_alpha(self, alpha):
        """
        Dynamically adjust the filter coefficient
        
        Args:
            alpha: New filter coefficient (0.0-1.0)
        """
        self.alpha = max(0.01, min(0.5, alpha))

# Class for handling multi-dimensional spin detection
class SpinDetector:
    def __init__(self, buffer_size=30, damping_factor=0.999):
        """
        Initialize spin detector with support for multiple dimensions
        
        Args:
            buffer_size: Size of the buffer for DFT calculation
            damping_factor: Damping factor for DFT
        """
        # Initialize DFT for each dimension
        self.x_dft = DFTHelper(buffer_size=buffer_size, damping_factor=damping_factor)
        self.y_dft = DFTHelper(buffer_size=buffer_size, damping_factor=damping_factor)
        self.z_dft = DFTHelper(buffer_size=buffer_size, damping_factor=damping_factor)
        
        # Initialize filters for each dimension
        self.x_filter = SpinRemovalFilter(alpha=0.05)
        self.y_filter = SpinRemovalFilter(alpha=0.05)
        self.z_filter = SpinRemovalFilter(alpha=0.05)
        
        # Combined spin magnitude
        self.combined_magnitude = 0.0
        
        # Adaptive threshold based on target properties
        self.adaptive_threshold = SPIN_MAGNITUDE_THRESHOLD
        
        # Store information about spinning pattern
        self.is_spinning = False
        self.spin_plane = "unknown"  # xy, xz, yz, or 3d
        self.spin_rate = 0.0  # cycles per second
        
    def update(self, position, target_size=None, target_distance=None):
        """
        Update spin detector with new position measurements
        
        Args:
            position: Position vector (x, y, z)
            target_size: Optional size of target for adaptive thresholding
            target_distance: Optional distance to target for adaptive thresholding
            
        Returns:
            bool: True if spinning is detected
        """
        # Extract components
        x, y, z = position
        
        # Update DFTs for each dimension
        x_valid = self.x_dft.update(x)
        y_valid = self.y_dft.update(y)
        z_valid = self.z_dft.update(z) if z is not None else False
        
        # Only proceed if we have enough data
        if not (x_valid and y_valid):
            return False
        
        # Get spin magnitudes for each axis
        x_magnitude = self.x_dft.get_spin_magnitude()
        y_magnitude = self.y_dft.get_spin_magnitude()
        z_magnitude = self.z_dft.get_spin_magnitude() if z_valid else 0.0
        
        # Combined spin magnitude (using root sum of squares)
        self.combined_magnitude = np.sqrt(x_magnitude**2 + y_magnitude**2 + z_magnitude**2)
        
        # Adjust threshold based on target properties if available
        if target_distance is not None:
            # Targets further away need higher threshold (harder to detect small movements)
            distance_factor = min(1.5, max(0.8, target_distance / 3.0))
            self.adaptive_threshold = SPIN_MAGNITUDE_THRESHOLD * distance_factor
        
        if target_size is not None:
            # Smaller targets need lower threshold (potentially more jitter)
            size_factor = min(1.2, max(0.8, 1.0 / target_size))
            self.adaptive_threshold = self.adaptive_threshold * size_factor
        
        # Determine spin plane based on relative magnitudes
        if z_valid:
            max_mag = max(x_magnitude, y_magnitude, z_magnitude)
            if max_mag > 0:
                x_ratio = x_magnitude / max_mag
                y_ratio = y_magnitude / max_mag
                z_ratio = z_magnitude / max_mag
                
                if x_ratio > 0.7 and y_ratio > 0.7:
                    self.spin_plane = "xy"
                elif x_ratio > 0.7 and z_ratio > 0.7:
                    self.spin_plane = "xz"
                elif y_ratio > 0.7 and z_ratio > 0.7:
                    self.spin_plane = "yz"
                else:
                    self.spin_plane = "3d"
        else:
            self.spin_plane = "xy"
        
        # Calculate spin rate
        dom_freq_idx = self.x_dft.get_dominant_frequency()
        if dom_freq_idx > 0:
            self.spin_rate = dom_freq_idx / buffer_size
        
        # Detect if spinning
        self.is_spinning = self.combined_magnitude > self.adaptive_threshold
        
        # Adjust filter parameters based on spin characteristics
        if self.is_spinning:
            # Faster spins need more aggressive filtering
            filter_alpha = max(0.01, min(0.1, 0.05 / (self.combined_magnitude)))
            self.x_filter.set_alpha(filter_alpha)
            self.y_filter.set_alpha(filter_alpha)
            self.z_filter.set_alpha(filter_alpha)
        
        return self.is_spinning
    
    def get_filtered_position(self, position):
        """
        Get filtered position that removes spin oscillations
        
        Args:
            position: Original position (x, y, z)
            
        Returns:
            tuple: Filtered position
        """
        x, y, z = position
        
        # Apply filters only if spinning detected
        if self.is_spinning:
            x_filtered = self.x_filter.update(x)
            y_filtered = self.y_filter.update(y)
            z_filtered = self.z_filter.update(z) if z is not None else None
            
            return (x_filtered, y_filtered, z_filtered)
        else:
            # If not spinning, just return original position
            return position
    
    def predict_position(self, position, time_delta):
        """
        Predict position accounting for spin pattern
        
        Args:
            position: Current position
            time_delta: Time to predict ahead
            
        Returns:
            tuple: Predicted position accounting for spin
        """
        if not self.is_spinning or self.combined_magnitude < self.adaptive_threshold:
            return position
        
        x, y, z = position
        
        # Get filtered position (center of spin)
        x_center, y_center, z_center = self.get_filtered_position(position)
        
        # Get spin characteristics
        x_freq = self.x_dft.get_dominant_frequency()
        y_freq = self.y_dft.get_dominant_frequency()
        x_phase = self.x_dft.get_phase()
        y_phase = self.y_dft.get_phase()
        x_amp = self.x_dft.get_amplitude()
        y_amp = self.y_dft.get_amplitude()
        
        # Only apply predictive adjustment if we have valid dominant frequencies
        if x_freq > 0 and y_freq > 0:
            # Calculate phase advance for the time delta
            phase_advance = 2 * np.pi * (x_freq / self.x_dft.buffer_size) * time_delta
            
            # Predict future position by adding predicted spin oscillation to filtered center
            if self.spin_plane == "xy" or self.spin_plane == "3d":
                adjustment_factor = SPIN_ADJUSTMENT_FACTOR * min(1.0, self.combined_magnitude / 0.3)
                x_pred = x_center + adjustment_factor * x_amp * np.cos(x_phase + phase_advance)
                y_pred = y_center + adjustment_factor * y_amp * np.cos(y_phase + phase_advance)
                z_pred = z_center if z_center is not None else None
                
                return (x_pred, y_pred, z_pred)
        
        # If we can't make a good prediction, just return filtered position
        return (x_center, y_center, z_center)

# 
# config
# 
MIN_RANGE           = config.aiming.min_range
MAX_RANGE           = config.aiming.max_range
CAMERA              = config.hardware.camera
DEPTH_COMPATIBLE    = config.hardware.camera_has_depth
POSE_COMPATIBLE     = config.hardware.camera_has_pose

# Spin detection configuration (matching comp/spin-detection)
SPIN_DETECTION_ENABLED = True    # Master switch to enable/disable spin detection
SPIN_BUFFER_SIZE = 30            # DFT buffer size (same as x_dft_size in comp/spin-detection)
SPIN_DAMPING_FACTOR = 0.999      # Damping factor (same as dampingValue in comp/spin-detection)
SPIN_MAGNITUDE_THRESHOLD = 0.15  # Threshold for spin detection (from comp/spin-detection)

SPIN_ADJUSTMENT_FACTOR = 1.0     # Global multiplier for all spin adjustments
                                 # Increase (1.5-2.0) to make adjustments more aggressive
                                 # Decrease (0.5-0.8) if adjustments are overshooting
                                 # This is the easiest parameter to tune for overall system performance

# Initialize spin detector with configurable parameters
spin_detector = SpinDetector(buffer_size=SPIN_BUFFER_SIZE, damping_factor=SPIN_DAMPING_FACTOR)

# Position filter for removing spin (heavy filtering)
# This is used when spin is detected to get a more stable position
class SpinRemovalFilter:
    def __init__(self, alpha=0.05):
        """
        Simple exponential filter for removing spin from position data
        
        Args:
            alpha: Filter coefficient (0.0-1.0)
                  Lower values provide more filtering (smoother output)
                  Higher values respond faster to changes
        """
        self.filtered_value = 0.0
        self.alpha = alpha
        self.initialized = False
        
    def update(self, new_value):
        """
        Update the filter with a new position value
        
        Args:
            new_value: New position value
            
        Returns:
            float: Filtered position value
        """
        if not self.initialized:
            self.filtered_value = new_value
            self.initialized = True
            return self.filtered_value
            
        # Apply exponential filter: y[n] = α*x[n] + (1-α)*y[n-1]
        self.filtered_value = self.alpha * new_value + (1 - self.alpha) * self.filtered_value
        return self.filtered_value

# Initialize DFT for X position
x_dft = DFTHelper(buffer_size=SPIN_BUFFER_SIZE, damping_factor=SPIN_DAMPING_FACTOR)
# Initialize spin removal filter (heavy filtering for removing spin)
x_spin_removal_filter = SpinRemovalFilter(alpha=0.05)
# Spin detection parameters
spin_magnitude = 0.0
x_position_spin_removed = 0.0

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
    spin_magnitude=0.0
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
    target_kinematic_state  = None

    validBoxes          = []
    validConfidences    = []
    valid3dTargets      = []

    best_bounding_box   = None
    current_confidence  = 0
    best_target_3d      = Position((0,0,0))
    
    # Store spin information
    spin_magnitude = 0.0
    spin_is_detected = False
    spin_prediction = None

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
            
            # Enhanced Spin Detection (3D version)
            if SPIN_DETECTION_ENABLED:
                # Get target size for adaptive thresholding
                target_size = best_bounding_box.width * best_bounding_box.height / (runtime.color_image.shape[0] * runtime.color_image.shape[1])
                
                # Update spin detector with current 3D position
                spin_is_detected = spin_detector.update(
                    position=best_target_3d,
                    target_size=target_size,
                    target_distance=measurement[1]  # Y is depth
                )
                
                # Store spin magnitude for logging
                spin_magnitude = spin_detector.combined_magnitude
                
                # If spin detected, use filtered position for Kalman update
                if spin_is_detected:
                    filtered_position = spin_detector.get_filtered_position(best_target_3d)
                    print(f"3D Spin detected! Magnitude: {spin_magnitude:.4f}")
                    print(f"Spin plane: {spin_detector.spin_plane}, Rate: {spin_detector.spin_rate:.2f} Hz")
                    print(f"Using filtered position: {filtered_position}")
                    
                    # Update measurement with filtered position
                    measurement = np.array(filtered_position, dtype=np.float32)
            
            # Kalman filter prediction
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
            print(f"dt aim.py: {frame_delay}")
            print(f"pos aim.py: {forward_prediction[0]}, {forward_prediction[3]}, {forward_prediction[6]}")
            target_kinematic_state = forward_prediction
            target_3d_prediction = Position((forward_prediction[0], forward_prediction[3], forward_prediction[6]))
            
            # Apply enhanced spin prediction if spinning
            if SPIN_DETECTION_ENABLED and spin_is_detected:
                # Convert Position to tuple for spin prediction
                position_tuple = (target_3d_prediction.x, target_3d_prediction.y, target_3d_prediction.z)
                
                # Get spin-adjusted prediction
                spin_adjusted_prediction = spin_detector.predict_position(
                    position=position_tuple,
                    time_delta=frame_delay
                )
                
                # Update prediction with spin compensation
                target_3d_prediction = Position(spin_adjusted_prediction)
                print(f"Applied spin prediction adjustment: {spin_adjusted_prediction}")
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
            
            # Enhanced Spin Detection (2D version)
            if SPIN_DETECTION_ENABLED:
                # Get target size for adaptive thresholding
                target_size = best_bounding_box.width * best_bounding_box.height / (runtime.color_image.shape[0] * runtime.color_image.shape[1])
                
                # For 2D detection, use special position format (x, y, None)
                spin_is_detected = spin_detector.update(
                    position=(center_point.x, center_point.y, None),
                    target_size=target_size,
                    target_distance=None  # No depth in 2D mode
                )
                
                # Store spin magnitude for logging
                spin_magnitude = spin_detector.combined_magnitude
                
                # If spin detected, use filtered position for Kalman update
                if spin_is_detected:
                    filtered_position = spin_detector.get_filtered_position((center_point.x, center_point.y, None))
                    print(f"2D Spin detected! Magnitude: {spin_magnitude:.4f}")
                    print(f"Using filtered position: {filtered_position[0]}, {filtered_position[1]}")
                    
                    # Update measurement with filtered position
                    measurement = np.array([filtered_position[0], filtered_position[1]], dtype=np.float32)
            
            # Kalman filter prediction
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
            
            # Apply enhanced spin prediction if spinning
            if SPIN_DETECTION_ENABLED and spin_is_detected:
                # Convert Position to tuple for spin prediction
                position_tuple = (center_point_prediction.x, center_point_prediction.y, None)
                
                # Get spin-adjusted prediction
                spin_adjusted_prediction = spin_detector.predict_position(
                    position=position_tuple,
                    time_delta=frame_delay
                )
                
                # Update prediction with spin compensation
                center_point_prediction = Position((spin_adjusted_prediction[0], spin_adjusted_prediction[1]))
                print(f"Applied 2D spin prediction adjustment")
   
   
    # update the shared data
    runtime.aiming.target_status            = TargetStatus.TARGET_NONE if best_bounding_box is None else TargetStatus.TARGET_FOUND
    runtime.aiming.target_3d                = best_target_3d
    runtime.aiming.center_point             = center_point
    runtime.aiming.center_point_prediction  = center_point_prediction
    runtime.aiming.best_bounding_box        = best_bounding_box
    runtime.aiming.current_confidence       = current_confidence
    runtime.aiming.spin_magnitude           = spin_magnitude
    runtime.aiming.target_3d_prediction     = target_3d_prediction
    runtime.aiming.target_kinematic_state   = target_kinematic_state
    runtime.aiming.is_spinning              = spin_is_detected if SPIN_DETECTION_ENABLED else False
    if SPIN_DETECTION_ENABLED and spin_is_detected:
        runtime.aiming.spin_plane           = spin_detector.spin_plane
        runtime.aiming.spin_rate            = spin_detector.spin_rate


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

def adjust_prediction_for_spin(target_position, spin_magnitude, x_position_spin_removed):
    """
    Adjust target prediction based on detected spin pattern
    
    This function is kept for backward compatibility but is now deprecated.
    The new SpinDetector class handles all spin prediction adjustments.
    
    Args:
        target_position: Current predicted target position (Position object)
        spin_magnitude: Magnitude of spin detected by DFT
        x_position_spin_removed: Filtered X position with spin removed
        
    Returns:
        Position: The same target position (no additional adjustment)
    """
    print("Warning: Using deprecated adjust_prediction_for_spin function. Spin handling is now done by SpinDetector.")
    return target_position
