# Chapter 7: Aiming Subsystem (`aim`)

In the [previous chapter](06_boundingbox_.md), we learned about the `BoundingBox`, which is like drawing a rectangle around a detected enemy robot in the flat, 2D camera image. That's great for knowing *where* the target is *on the screen*.

But our robot needs to aim its turret or weapon in the real, 3D world! How do we go from a 2D rectangle on a screen to knowing the actual X, Y, and Z coordinates of the target in front of the robot? And what if the [Model Subsystem](05_model_subsystem_.md) finds *multiple* enemy robots? Which one should we aim at?

## The Problem: From 2D Boxes to 3D Aiming Points

Imagine you're playing a video game where you click on targets on the screen. The game needs to figure out where that target actually *is* in the game's 3D world to calculate the bullet's path. Our robot needs to do something similar.

The challenges are:
1.  **Multiple Targets:** The [Model Subsystem](05_model_subsystem_.md) might give us several `BoundingBox`es. How do we decide which one is the *best* target? Should we aim at the closest one? The one nearest the center of the screen? The biggest one?
2.  **2D to 3D:** A `BoundingBox` tells us the target's location in the 2D image pixels (like "x=320, y=240"). We need to convert this into real-world 3D coordinates relative to the camera (like "X=0.1 meters right, Y=0.05 meters down, Z=2.5 meters forward"). This requires knowing the target's *distance*.

## The Solution: `aim` - The Targeting Computer

The **Aiming Subsystem (`aim`)** acts like the robot's targeting computer. It takes the list of potential targets (enemy `BoundingBox`es) found by the [Model Subsystem](05_model_subsystem_.md) and figures out the final aiming solution.

Its main jobs are:

1.  **Target Selection:** If there are multiple enemy `BoundingBox`es, it uses logic to choose the "optimal" one. This logic might consider:
    *   **Proximity to Center:** Targets closer to the center of the camera's view might be preferred.
    *   **Size:** Larger boxes might indicate closer or more important targets.
    *   **Confidence:** Targets the [Model Subsystem](05_model_subsystem_.md) was more confident about might be prioritized.
    *   **Distance (Depth):** If the camera provides depth information (like a ZED or RealSense camera), the closest valid target might be chosen.
2.  **3D Coordinate Calculation:** Once the best 2D `BoundingBox` is chosen, the `aim` subsystem calculates the target's real-world 3D coordinates (X, Y, Z).
    *   It uses the center point of the chosen `BoundingBox`.
    *   Crucially, if the [Video Stream Subsystem](04_video_stream_subsystem_.md) provides a `depth_image`, the `aim` subsystem uses the depth value at the target's location to estimate the distance (Z).
    *   Using the camera's internal properties (its "intrinsics", handled by the video stream helpers) and the 2D pixel location + depth, it can calculate the real-world X and Y coordinates relative to the camera's center.

The final output is a single 3D point (X, Y, Z) representing where the robot should aim.

## How the Main Loop Uses `aim`

The `aim` subsystem does its work after the `model` has found potential targets.

```python
# File: main.py (Simplified loop)

from subsystems import video_stream, model, aim # Import subsystems
from toolbox.globals import runtime # Import shared data

# Get frame and put it in runtime
for runtime.frame_number, runtime.color_image, runtime.depth_image in video_stream.frames():

    # 1. Model finds targets in the image
    model.when_frame_arrives()
    # Results (enemy_boxes, confidences) are now in runtime.modeling

    # ---> 2. Aim decides which target to shoot and where <---
    aim.when_bounding_boxes_refresh()
    # Aiming results (target_3d, target_status) are now in runtime.aiming

    # 3. Communication sends the aiming command
    # communicate.when_aiming_refreshes()
    # ... (log) ...
```

1.  The [Model Subsystem](05_model_subsystem_.md) runs `model.when_frame_arrives()`, putting a list of enemy `BoundingBox`es and their confidences into `runtime.modeling.enemy_boxes` and `runtime.modeling.confidences`.
2.  The main loop then calls `aim.when_bounding_boxes_refresh()`. This tells the Aiming Subsystem: "Look at the `enemy_boxes` in `runtime`. Pick the best one and calculate where to aim in 3D."

Inside `aim.when_bounding_boxes_refresh()` (in `subsystems/aim.py`), the subsystem reads from and writes to the `runtime` blackboard:

```python
# File: subsystems/aim.py (Conceptual 'when_bounding_boxes_refresh')

from toolbox.globals import runtime, config # Use runtime and config
from toolbox.geometry_tools import Position # For representing points
from enum import Enum # For defining status codes

class TargetStatus(Enum): # Define possible outcomes
    TARGET_NONE = 0
    TARGET_FOUND = 1
    # TARGET_ENGAGE = 2 # Maybe used later

def when_bounding_boxes_refresh():
    # --- Inputs read from runtime ---
    enemy_boxes = runtime.modeling.enemy_boxes         # List of BoundingBoxes
    enemy_confidences = runtime.modeling.confidences   # List of confidences
    depth_image = runtime.depth_image                  # Depth data (if available)
    screen_center = runtime.screen_center              # Center pixel of the image
    has_depth = config.hardware.camera_has_depth       # Check config if depth is expected

    # --- Logic (Simplified) ---
    best_box = None
    best_confidence = 0
    best_target_3d = None
    target_status = TargetStatus.TARGET_NONE

    valid_targets = [] # To store potential targets with 3D info

    # 1. Filter boxes and get 3D coordinates (if depth available)
    if has_depth:
        for box, confidence in zip(enemy_boxes, enemy_confidences):
            # Estimate distance using depth_image near box.center
            estimated_distance = get_dist_to_bbox(box) # Helper function (explained later)
            
            # Check if distance is within acceptable range (from config)
            if estimated_distance is None or not (config.aiming.min_range < estimated_distance < config.aiming.max_range):
                continue # Skip this box if distance is invalid

            # Calculate 3D point (X, Y, Z) using box.center and distance
            target_3d = get_xyz_at_color_coords(box.center, estimated_distance) # Helper (explained later)
            if target_3d is None:
                continue # Skip if 3D calculation failed

            # Add valid target info to our list
            valid_targets.append({'box': box, 'confidence': confidence, 'target_3d': target_3d})
    else:
        # If no depth, we can't easily get 3D. Maybe just pick best 2D box?
        # (Project code assumes depth for 3D aiming)
        pass # Simplified for tutorial

    # 2. Select the best target from the valid ones
    if valid_targets:
        # Use logic to pick the best based on score (distance, center proximity, etc.)
        best_target_info = get_optimal_3d_target(valid_targets, screen_center) # Helper (explained later)
        
        if best_target_info:
            best_box = best_target_info['box']
            best_confidence = best_target_info['confidence']
            best_target_3d = best_target_info['target_3d']
            target_status = TargetStatus.TARGET_FOUND

    # --- Outputs written to runtime ---
    runtime.aiming.target_status = target_status        # Did we find a target?
    runtime.aiming.target_3d = best_target_3d           # The final (X, Y, Z) aim point
    
    # Also update some 'modeling' fields for logging/display convenience
    runtime.modeling.best_bounding_box = best_box       # The chosen 2D box
    runtime.modeling.current_confidence = best_confidence # Confidence of the chosen box
    runtime.modeling.found_robot = (best_box is not None) # Simple boolean flag
    # Store the 2D center point of the best box too
    runtime.aiming.center_point = Position(best_box.center) if best_box else Position((0,0))

```

This function:
1.  Reads the list of enemy boxes and confidences from `runtime.modeling`.
2.  Reads the `runtime.depth_image` (if the camera provides it, checked via `config`).
3.  If depth is available, it loops through the boxes:
    *   Estimates the distance using a helper `get_dist_to_bbox`.
    *   Checks if the distance is valid (within `min_range` and `max_range` from `config`).
    *   Calculates the 3D coordinates (X, Y, Z) using another helper `get_xyz_at_color_coords`.
    *   Stores valid targets (box, confidence, 3D point) in a list.
4.  If there are valid targets, it calls `get_optimal_3d_target` to choose the best one based on a scoring system.
5.  Writes the final results (`target_status`, `target_3d`) to `runtime.aiming`.
6.  It also updates `runtime.modeling` with details about the *chosen* target (`best_bounding_box`, `current_confidence`) for easy access by the [Logging Subsystem (`log`)](09_logging_subsystem___log___.md).

## Under the Hood: Calculating and Choosing

Let's peek at the concepts behind those helper functions:

**1. Estimating Distance (`get_dist_to_bbox`)**

How do you get a reliable distance reading for a target that fills a whole `BoundingBox`? Just picking the depth value at the exact center pixel might be noisy or inaccurate (e.g., hitting a small hole in the armor).

The `get_dist_to_bbox` function is smarter:
*   It defines a small area *inside* the center of the `BoundingBox`.
*   It samples several depth points within this small area from the `runtime.depth_image`.
*   It filters out strange values (like 0, which often means "no reading", or values that are statistical outliers compared to the others in the sample using techniques like Median Absolute Deviation).
*   It calculates the *average* of the remaining valid depth readings.
*   This average depth gives a more robust estimate of the target's distance (Z).

**2. Calculating 3D Coordinates (`get_xyz_at_color_coords`)**

Once we have the 2D center point (`box.center`) and the estimated distance (`estimated_distance`), how do we get X and Y?

This involves some camera math. Think of the camera like a projector in reverse. It knows the relationship between a pixel location (like `box.center`) and the direction that pixel represents in the real world. If you also tell it the distance along that direction (`estimated_distance`), it can calculate the corresponding X and Y coordinates relative to the camera's own center axis.

Our [Video Stream Subsystem](04_video_stream_subsystem_.md) (specifically the code for depth cameras like RealSense or ZED) often provides a helper function (like `video_stream.get_xyz_at_color_point`) that does this complex math for us. The `aim` subsystem just needs to call it with the 2D point and the estimated depth.

**3. Choosing the Optimal Target (`get_optimal_3d_target`)**

If we have multiple valid targets (with boxes, confidences, and 3D points), how do we pick the best one?

The `get_optimal_3d_target` function calculates a "score" for each valid target. The score might be a combination of factors, weighted according to importance:
*   `size_score`: How big is the box on screen? (Maybe bigger is better?)
*   `center_score`: How close is the box center to the screen center? (Closer is often better.)
*   `conf_score`: How confident was the model? (Higher confidence is better.)
*   `depth_score`: How far away is the target (based on its Z coordinate)? (Maybe closer targets get a higher score?)
*   `circle_bias_score`: How close is this target to where we aimed *last* frame? (Prioritizing targets near the previous aim point can help stabilize aiming).

The function combines these into a final score for each target. The target with the highest score is declared the "optimal" target for this frame. The exact weights used in the score calculation are tweaked to get the desired aiming behavior.

```python
# File: subsystems/aim.py (Conceptual scoring inside get_optimal_3d_target)

def get_optimal_3d_target(valid_targets, screen_center):
    best_target = None
    best_score = -1 # Start with a very low score

    for target_info in valid_targets:
        box = target_info['box']
        conf = target_info['confidence']
        target_3d = target_info['target_3d']

        # --- Calculate individual score components ---
        # (Simplified formulas)
        size_score = box.area / (runtime.color_image.shape[0] * runtime.color_image.shape[1]) # Area relative to screen
        center_dist = dist(screen_center, box.center)
        center_score = max(0, 1 - center_dist / (screen_center[0])) # Score higher if closer to center
        conf_score = conf
        depth_score = max(0, 1 - target_3d[2] / config.aiming.max_range) # Score higher if closer (lower Z)
        
        # --- Combine scores (example weights) ---
        total_score = (0.2 * size_score + 
                       0.4 * center_score + 
                       0.1 * conf_score + 
                       0.3 * depth_score)

        # --- Update best target if this one is better ---
        if total_score > best_score:
            best_score = total_score
            best_target = target_info
            
    return best_target # Return the dictionary containing info of the best target
```

**Simplified Workflow Diagram**

```mermaid
sequenceDiagram
    participant Loop as Main Loop
    participant Aim as Aiming Subsystem (aim)
    participant RT as runtime Blackboard
    participant VS as Video Stream Helpers

    Loop->>Aim: Call when_bounding_boxes_refresh()
    Aim->>RT: Read enemy_boxes, confidences, depth_image
    loop For each enemy_box
        Aim->>Aim: Estimate distance (get_dist_to_bbox using depth_image)
        Aim->>VS: Get 3D point (get_xyz_at_color_coords using box.center, distance)
        VS-->>Aim: Provides (X, Y, Z) or None
        Aim->>Aim: Store valid target info
    end
    Aim->>Aim: Select best target (get_optimal_3d_target using scoring)
    Aim->>RT: Write aiming.target_3d, aiming.target_status
    Aim->>RT: Write modeling.best_bounding_box, etc.
    Aim-->>Loop: Done for this frame
```

## Conclusion

The **Aiming Subsystem (`aim`)** is the brain that translates the visual detections from the [Model Subsystem](05_model_subsystem_.md) into actionable 3D aiming commands. It intelligently selects the best target from multiple possibilities and, using depth information provided by the [Video Stream Subsystem](04_video_stream_subsystem_.md), calculates the target's precise X, Y, and Z coordinates in the real world.

By reading inputs like `BoundingBox`es and depth images from the [Shared Runtime Data (`runtime`)](03_shared_runtime_data___runtime___.md) blackboard and writing back the calculated `target_3d` and `target_status`, it acts as the crucial link between seeing the target and knowing exactly where to point.

Now that we have the desired aiming coordinates (X, Y, Z), how do we actually send this information to the physical motors or actuators that control the robot's turret or weapon? That's the job of our next component.

Next: [Chapter 8: Communication Subsystem (`communicate`)](08_communication_subsystem___communicate___.md)

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)