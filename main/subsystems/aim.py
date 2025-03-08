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


# NOTE initial kinematic state is set to all ones. This might effect convergence time
# TODO find better uncertainty for x, y, z
kf_2d = KF2D(np.ones((6,1), dtype=np.float32), 0.1, 0.1, 0.05, 0.05)
kf_3d = KF3D(np.ones((9,1), dtype=np.float32), 0.1, 0.1, 0.1, 0.05, 0.2)


# DFT implementation for spin detection
class DFTHelper:
    def __init__(self, buffer_size=30, damping_factor=0.999):
        """
        Initialize DFT helper for spin detection
        
        The Discrete Fourier Transform (DFT) is used to detect periodic patterns in the target's movement,
        which can indicate spinning or oscillating behavior. This is particularly useful for:
        1. Detecting if a target is spinning/rotating
        2. Determining the frequency of rotation
        3. Adjusting aim prediction based on the detected pattern
        
        Args:
            buffer_size: Size of the buffer for DFT calculation. Larger buffers can detect slower
                         frequency patterns but take longer to fill with data. A buffer of 30 samples
                         provides a good balance between detection speed and frequency resolution.
            
            damping_factor: Controls how quickly older samples decay in importance (0.0-1.0).
                            Values closer to 1.0 make the DFT more stable but slower to adapt to changes.
                            Values closer to 0.0 make the DFT more responsive but potentially noisier.
                            The value 0.999 provides a good balance for most scenarios.
        """
        self.buffer_size = buffer_size
        self.damping_factor = damping_factor
        # Initialize buffer with zeros - this will store position samples over time
        self.buffer = np.zeros(buffer_size, dtype=np.float32)
        # Initialize DFT output array - will contain complex frequency components
        self.dft = np.zeros(buffer_size, dtype=np.complex64)
        # DFT is not valid until buffer has sufficient non-zero values
        self.is_valid = False
        # Threshold indices for middle frequency range (similar to spindetect.cpp)
        self.dft_threshold_1 = buffer_size // 4
        self.dft_threshold_2 = 3 * (buffer_size // 4)
        # Simple filter for smoothing spin magnitude
        self.spin_magnitude_filter = 0.0
        self.spin_filter_alpha = 0.2  # Filter coefficient (0.0-1.0)
        
    def update(self, new_value):
        """
        Update the DFT with a new position value
        
        This method:
        1. Applies damping to the existing buffer (giving less weight to older samples)
        2. Shifts the buffer and adds the new value
        3. Recalculates the DFT
        4. Determines if the DFT is now valid
        
        The damping creates a "fading memory" effect, where recent samples have more influence
        than older ones. This helps the DFT adapt to changes in movement patterns over time.
        
        Args:
            new_value: New position value to add to the buffer (typically x-coordinate)
            
        Returns:
            bool: True if DFT is valid (buffer has enough samples), False otherwise
        """
        # Apply damping factor to existing buffer (exponential decay of old samples)
        self.buffer = self.buffer * self.damping_factor
        # Shift buffer left and add new value at the end
        self.buffer = np.roll(self.buffer, -1)
        self.buffer[-1] = new_value
        
        # Calculate DFT using Fast Fourier Transform
        # The resulting self.dft array contains complex numbers representing:
        # - Magnitude (absolute value): strength of each frequency component
        # - Phase (angle): timing/offset of each frequency component
        self.dft = np.fft.fft(self.buffer)
        
        # DFT is considered valid once the buffer contains enough non-zero values
        # This prevents making predictions based on insufficient data
        if not self.is_valid and np.count_nonzero(self.buffer) >= self.buffer_size:
            self.is_valid = True
            
        return self.is_valid
    
    def is_data_valid(self):
        """
        Check if the DFT data is valid (buffer is filled with enough samples)
        
        Returns:
            bool: True if DFT is valid, False otherwise
        """
        return self.is_valid
    
    def get_spin_magnitude(self):
        """
        Calculate spin magnitude by analyzing the middle frequency range
        
        Following the approach in spindetect.cpp, this method:
        1. Calculates the average magnitude of frequency components in the middle range
        2. Applies a simple filter to smooth the result
        3. Returns the filtered magnitude
        
        The middle frequency range (1/4 to 3/4 of buffer size) typically contains
        the most relevant frequencies for detecting spinning or oscillating motion.
        
        Returns:
            float: Filtered spin magnitude
        """
        if not self.is_valid:
            return 0.0
        
        # Calculate average magnitude in the middle frequency range
        magnitude_avg_middle_half = 0.0
        count = 0
        
        for i in range(self.dft_threshold_1, self.dft_threshold_2):
            # Calculate magnitude of complex number (sqrt(real² + imag²))
            magnitude = np.abs(self.dft[i])
            magnitude_avg_middle_half += magnitude
            count += 1
            
        # Average the magnitudes
        if count > 0:
            magnitude_avg_middle_half /= count
            
        # Apply simple low-pass filter to smooth the magnitude
        # new_value = alpha * current_input + (1-alpha) * previous_value
        self.spin_magnitude_filter = (self.spin_filter_alpha * magnitude_avg_middle_half + 
                                     (1 - self.spin_filter_alpha) * self.spin_magnitude_filter)
        
        return self.spin_magnitude_filter
    
    def get_dominant_frequency(self):
        """
        Get the dominant frequency component (excluding DC)
        
        The dominant frequency indicates the main rate at which the target is spinning:
        - Lower indices (1-5): slow rotation/oscillation
        - Middle indices (6-15): medium speed rotation
        - Higher indices (16+): fast rotation
        
        Note: The actual frequency in Hz depends on the sampling rate of position data.
        For a system running at 30fps, frequency bin 3 would represent ~3Hz or
        3 complete rotations per second.
        
        Returns:
            int: Index of dominant frequency (1 to buffer_size-1)
        """
        if not self.is_valid:
            return 0
        
        # Skip DC component (index 0)
        magnitudes = np.abs(self.dft[1:])
        # Find index of maximum magnitude
        max_index = np.argmax(magnitudes) + 1  # +1 because we skipped DC
        
        return max_index


# 
# config
# 
MIN_RANGE           = config.aiming.min_range
MAX_RANGE           = config.aiming.max_range
CAMERA              = config.hardware.camera
DEPTH_COMPATIBLE    = config.hardware.camera_has_depth
POSE_COMPATIBLE     = config.hardware.camera_has_pose

# Spin detection configuration
# These could be moved to the config file in the future
SPIN_DETECTION_ENABLED = True    # Master switch to enable/disable all spin detection
SPIN_BUFFER_SIZE = 30            # Number of samples to keep in DFT buffer
                                 # Larger values (40-60) detect slower patterns but take longer to fill
                                 # Smaller values (15-25) respond faster but may miss slower patterns
                                 # 30 is a good balance for most scenarios

SPIN_DAMPING_FACTOR = 0.999      # Controls how quickly older samples decay in importance (0.0-1.0)
                                 # Higher values (0.999-0.9999) make detection more stable but slower to adapt
                                 # Lower values (0.99-0.995) make detection more responsive but potentially noisier
                                 # 0.999 works well for most scenarios

SPIN_MAGNITUDE_THRESHOLD = 0.15  # Minimum spin magnitude to trigger adjustment (from spindetect.cpp)
                                 # Higher values (0.2-0.3) only adjust for very clear spinning patterns
                                 # Lower values (0.1-0.15) are more sensitive but may adjust unnecessarily
                                 # 0.15 was found to work well in the original implementation

SPIN_ADJUSTMENT_FACTOR = 1.0     # Global multiplier for all spin adjustments
                                 # Increase (1.5-2.0) to make adjustments more aggressive
                                 # Decrease (0.5-0.8) if adjustments are overshooting
                                 # This is the easiest parameter to tune for overall system performance

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
# Initialize spin removal filter
x_spin_removal_filter = SpinRemovalFilter(alpha=0.05)
# Spin detection parameters
spin_magnitude = 0.0
dominant_frequency_bin = 0
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
    spin_magnitude=0.0,
    dominant_frequency=0
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

            # Update DFT with filtered X position for spin detection
            if SPIN_DETECTION_ENABLED:
                # We use the X position for spin detection because horizontal movement
                # is often the most indicative of rotation in many scenarios
                
                # Get the unfiltered X position (similar to spindetect.cpp)
                x_position = measurement[0]
                
                # Feed the new position into our DFT analyzer
                # This updates the internal buffer and recalculates the frequency spectrum
                x_dft.update(x_position)
                x_dft_valid = x_dft.is_data_valid()
                
                # Calculate spin magnitude if DFT is valid (buffer is filled)
                global spin_magnitude, dominant_frequency_bin, x_position_spin_removed
                if x_dft_valid:
                    # Get the overall magnitude of periodic motion in the middle frequency range
                    # Higher values indicate stronger spinning/oscillation
                    spin_magnitude = x_dft.get_spin_magnitude()
                    
                    # Get the dominant frequency of the motion
                    # This tells us how fast the target is spinning/oscillating
                    dominant_frequency_bin = x_dft.get_dominant_frequency()
                    
                    # Debug output for spin detection
                    # This helps with tuning the system and understanding target behavior
                    print(f"Spin magnitude: {spin_magnitude}")
                    print(f"Dominant frequency bin: {dominant_frequency_bin}")
                    
                    # Check if spin magnitude exceeds threshold (from spindetect.cpp)
                    if spin_magnitude > SPIN_MAGNITUDE_THRESHOLD:
                        # If spinning is detected, use heavily filtered position to remove spin
                        x_position_spin_removed = x_spin_removal_filter.update(x_position)
                        print(f"Spin detected! Using filtered position: {x_position_spin_removed}")
                        
                        # Use the spin-removed position for the Kalman filter update
                        # This creates a more stable prediction by removing the oscillations
                        measurement[0] = x_position_spin_removed
                    
                    # Interpretation guide:
                    # - spin_magnitude < 0.15: Little to no spinning
                    # - spin_magnitude 0.15-0.5: Moderate spinning
                    # - spin_magnitude > 0.5: Strong spinning/oscillation

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
            
            # Adjust prediction based on spin detection
            # This step modifies our aim point to compensate for spinning targets
            if SPIN_DETECTION_ENABLED and x_dft_valid and spin_magnitude > 0:
                # The Kalman filter prediction assumes linear motion, but spinning targets
                # follow circular or oscillating paths. This adjustment compensates for that.
                target_3d_prediction = adjust_prediction_for_spin(
                    target_3d_prediction, 
                    spin_magnitude, 
                    dominant_frequency_bin
                )
                # After this adjustment, our aim point should better anticipate
                # where the spinning target will be when our projectile arrives
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

            # Update DFT with filtered X position for spin detection (2D case)
            if SPIN_DETECTION_ENABLED:
                # In 2D tracking, we still use the X position to detect horizontal oscillations
                # This works well for targets moving back and forth or rotating in the image plane
                x_position = center_point.x
                
                # Update DFT with the unfiltered position
                x_dft.update(x_position)
                x_dft_valid = x_dft.is_data_valid()
                
                # Calculate spin magnitude if DFT is valid
                global spin_magnitude, dominant_frequency_bin, x_position_spin_removed
                if x_dft_valid:
                    # Calculate the strength of periodic motion
                    spin_magnitude = x_dft.get_spin_magnitude()
                    
                    # Determine the primary frequency of oscillation
                    dominant_frequency_bin = x_dft.get_dominant_frequency()
                    
                    # Debug output for spin detection
                    # The (2D) label helps distinguish these from 3D case logs
                    print(f"Spin magnitude (2D): {spin_magnitude}")
                    print(f"Dominant frequency bin (2D): {dominant_frequency_bin}")
                    
                    # Check if spin magnitude exceeds threshold (from spindetect.cpp)
                    if spin_magnitude > SPIN_MAGNITUDE_THRESHOLD:
                        # If spinning is detected, use heavily filtered position to remove spin
                        x_position_spin_removed = x_spin_removal_filter.update(x_position)
                        print(f"Spin detected (2D)! Using filtered position: {x_position_spin_removed}")
                        
                        # Use the spin-removed position for the Kalman filter update
                        # This creates a more stable prediction by removing the oscillations
                        measurement[0] = x_position_spin_removed

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
            
            # Adjust prediction based on spin detection
            # For 2D tracking, we apply a simpler adjustment than in the 3D case
            if SPIN_DETECTION_ENABLED and x_dft_valid and spin_magnitude > 0:
                # The adjustment primarily shifts the aim point horizontally
                # to compensate for oscillating or circular motion
                center_point_prediction = adjust_prediction_for_spin(
                    center_point_prediction, 
                    spin_magnitude, 
                    dominant_frequency_bin
                )
                # This adjustment helps hit targets that are moving in patterns
                # that the linear Kalman filter doesn't model well
   
   
    # update the shared data
    runtime.aiming.target_status            = TargetStatus.TARGET_NONE if best_bounding_box is None else TargetStatus.TARGET_FOUND
    runtime.aiming.target_3d                = best_target_3d
    runtime.aiming.center_point             = center_point
    runtime.aiming.center_point_prediction  = center_point_prediction
    runtime.aiming.best_bounding_box        = best_bounding_box
    runtime.aiming.current_confidence       = current_confidence
    runtime.aiming.spin_magnitude           = spin_magnitude
    runtime.aiming.dominant_frequency       = dominant_frequency_bin
    runtime.aiming.target_3d_prediction     = target_3d_prediction
    runtime.aiming.target_kinematic_state   = target_kinematic_state


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

def adjust_prediction_for_spin(target_position, spin_magnitude, dominant_frequency):
    """
    Adjust target prediction based on detected spin pattern
    
    This function applies adjustments to the predicted target position based on detected
    spinning or oscillating patterns. Following the approach in spindetect.cpp, it:
    
    1. Determines if the spin is significant enough to warrant adjustment
    2. If spinning is detected, the position has already been filtered during the
       Kalman filter update stage, so minimal additional adjustment is needed
    3. We may still apply small adjustments based on the dominant frequency
    
    Args:
        target_position: Current predicted target position (Position object)
        spin_magnitude: Magnitude of spin detected by DFT
        dominant_frequency: Dominant frequency bin from DFT
        
    Returns:
        Position: Adjusted target position
    """
    # Skip adjustment if spin detection is disabled or magnitude is below threshold
    if not SPIN_DETECTION_ENABLED or spin_magnitude < SPIN_MAGNITUDE_THRESHOLD:
        return target_position
    
    # Create a copy of the target position for adjustment
    adjusted_position = Position(target_position)
    
    # In spindetect.cpp, most of the spin handling is done by using a heavily filtered
    # position for the Kalman filter update when spin is detected. This happens before
    # this function is called, so we don't need to make major adjustments here.
    
    # However, we can still make minor adjustments based on the dominant frequency
    # if needed for specific scenarios
    
    # Calculate a small adjustment factor based on dominant frequency
    # Higher frequencies might need slightly different handling
    freq_adjustment = 0.0
    if dominant_frequency > 15:  # High frequency spinning
        freq_adjustment = 0.05 * SPIN_ADJUSTMENT_FACTOR
    elif dominant_frequency > 5:  # Medium frequency spinning
        freq_adjustment = 0.03 * SPIN_ADJUSTMENT_FACTOR
    
    # Apply the small frequency-based adjustment if needed
    # This is a minimal adjustment since the main handling is done earlier
    if hasattr(target_position, 'z'):  # 3D position
        # For 3D positions, we might apply a small adjustment in the direction of motion
        # This is just a minor refinement on top of the filtered position
        adjusted_position.x += freq_adjustment
    else:  # 2D position
        # For 2D positions, similar small adjustment
        adjusted_position.x += freq_adjustment
    
    # Log the adjustment for debugging and tuning
    if freq_adjustment > 0:
        print(f"Additional spin adjustment: magnitude={spin_magnitude:.2f}, freq={dominant_frequency}, adj={freq_adjustment:.4f}")
    
    return adjusted_position
