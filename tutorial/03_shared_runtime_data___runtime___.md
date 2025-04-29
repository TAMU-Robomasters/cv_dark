# Chapter 3: Shared Runtime Data (`runtime`)

In the [previous chapter](02_global_configuration___config___.md), we learned about `config`, the central place for all the settings that tell our auto-aim system *how* to behave. Think of `config` as the system's instruction manual, set up *before* things start running.

But what about information that changes *while* the system is running? For example, in each cycle of the [Main Execution Loop](01_main_execution_loop_.md):
1.  The camera captures a new image (frame).
2.  The [Model Subsystem](05_model_subsystem_.md) analyzes this image and finds potential targets (like enemy robots).
3.  The [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md) needs to know *which* targets the Model found in *this specific frame* to calculate where to aim.

How does the information about the latest image and the detected targets get passed from one subsystem to the next within that single, fast processing cycle? They can't just look it up in the `config` file, because that data changes every few milliseconds!

## The Problem: Sharing Information *Now*

Imagine our assembly line again.
*   Station 1 (Camera) gets a fresh part (the image).
*   Station 2 (Model) inspects the part and attaches a note saying "Found a defect here!" (the target location).
*   Station 3 (Aiming) needs to read that *specific note* for *that specific part* to decide what to do next.

How do they pass these temporary notes quickly and reliably for each item on the line? They need a shared space where notes can be left and picked up almost instantly.

## The Solution: `runtime` - The Shared Blackboard

This is where **Shared Runtime Data (`runtime`)** comes in.

Think of `runtime` as a shared **blackboard** or a **temporary message board** right next to the assembly line.

*   When one subsystem (like the [Video Stream Subsystem](04_video_stream_subsystem_.md)) gets new information for the current frame (like the camera image), it writes it onto the `runtime` blackboard.
*   Later in the same frame processing cycle, another subsystem (like the [Model Subsystem](05_model_subsystem_.md)) can walk up to the blackboard and read that information.
*   If the Model subsystem produces new data (like a list of detected targets), it can also write *that* onto the `runtime` blackboard.
*   Then, the next subsystem (like the [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md)) can read both the original image *and* the list of targets from the blackboard.

This `runtime` object acts as a central, temporary holding place for data that needs to be shared between different parts of the code *during the processing of a single frame*. It's designed for speed and convenience within that short cycle.

## What's Inside `runtime`? (It's a `LazyDict`)

The `runtime` object is technically something called a `LazyDict`. Don't worry too much about the name! Just know it's like a super-flexible Python dictionary.

*   **Like a Dictionary:** It stores information using `key: value` pairs. For example, `runtime` might store the frame number like this: `frame_number: 123`.
*   **Flexible Organization:** You can organize data within it easily, almost like folders. For instance, the [Model Subsystem](05_model_subsystem_.md) might store its findings under a "modeling" section: `runtime.modeling.bounding_boxes = [list_of_boxes]`.
*   **"Lazy":** The "Lazy" part just means it's efficient. It doesn't create storage space for things until you actually put something there. If you ask for `runtime.modeling.some_new_thing`, and `runtime.modeling` didn't exist before, `LazyDict` automatically creates the `modeling` part for you. This makes it really easy to add new temporary data without a lot of setup code.

Common things you'll find being passed around via `runtime`:
*   `runtime.frame_number`: The number of the current frame being processed.
*   `runtime.color_image`: The actual image data from the camera for this frame.
*   `runtime.depth_image`: Depth information from the camera (if available).
*   `runtime.modeling.bounding_boxes`: A list of rectangles ([BoundingBox](06_boundingbox_.md)) where the model found potential targets.
*   `runtime.aiming.target_3d`: The calculated 3D coordinates the aiming system decided on.
*   `runtime.aiming.target_status`: Whether a target was found or not.

## How Subsystems Use `runtime`

Let's see how different parts of the code interact with `runtime`.

**1. Putting Data INTO `runtime`**

*   **Main Loop (`main.py`)**: Gets the new frame data from the video stream and puts it directly into `runtime`.

    ```python
    # File: main.py (Simplified loop start)
    # ... imports ...
    from subsystems import video_stream
    from toolbox.globals import runtime # Import runtime

    # The 'video_stream.frames()' function GIVES US the data
    # The 'for' loop ASSIGNS it directly to runtime variables
    for runtime.frame_number, runtime.color_image, runtime.depth_image in video_stream.frames():
        # Now, runtime.color_image holds the latest picture!
        # ... rest of the loop ...
    ```
    Here, each time the loop runs, the latest `frame_number`, `color_image`, and `depth_image` from the [Video Stream Subsystem](04_video_stream_subsystem_.md) are placed into `runtime`.

*   **Model Subsystem (`model.py`)**: Finds targets and puts the list of bounding boxes into `runtime`.

    ```python
    # File: subsystems/model.py (Simplified end of 'when_frame_arrives')
    # ... imports ...
    from toolbox.globals import runtime # Import runtime

    def when_frame_arrives():
        frame = runtime.color_image # Get image FROM runtime
        # ... model does its detection work ...
        all_boxes, confidences, class_ids = model.get_bounding_boxes(frame, ...)
        enemy_boxes, _, _ = filter_plate_color(all_boxes, ...)
        
        # Put the results INTO runtime for others to use
        runtime.modeling.bounding_boxes = all_boxes
        runtime.modeling.enemy_boxes = enemy_boxes
        runtime.modeling.confidences = confidences
        # ... other data ...
    ```
    After analyzing the `runtime.color_image`, the model places its results (`enemy_boxes`, etc.) into `runtime` under the `runtime.modeling` section.

*   **Aiming Subsystem (`aim.py`)**: Calculates the aiming point and puts it into `runtime`.

    ```python
    # File: subsystems/aim.py (Simplified end of 'when_bounding_boxes_refresh')
    # ... imports ...
    from toolbox.globals import runtime # Import runtime

    def when_bounding_boxes_refresh():
        enemy_boxes = runtime.modeling.enemy_boxes # Get boxes FROM runtime
        # ... aiming logic calculates the best target ...
        best_bounding_box, current_confidence, best_target_3d = get_optimal_3d_target(...)
        target_status = TargetStatus.TARGET_FOUND # Or TARGET_NONE
        center_point = Position(best_bounding_box.center) # if found

        # Put the aiming results INTO runtime
        runtime.aiming.target_status = target_status
        runtime.aiming.target_3d = best_target_3d
        runtime.aiming.center_point = center_point
        # ... also update some modeling results for logging ...
        runtime.modeling.best_bounding_box = best_bounding_box 
        # ...
    ```
    The aiming system reads the `runtime.modeling.enemy_boxes`, performs calculations, and then writes its conclusions (`target_status`, `target_3d`, etc.) back to `runtime` under the `runtime.aiming` section.

**2. Getting Data FROM `runtime`**

*   **Aiming Subsystem (`aim.py`)**: As seen above, it *reads* `runtime.modeling.enemy_boxes` to do its job.

*   **Communication Subsystem (`communicate.py`)**: Reads the final aiming coordinates from `runtime` to send them to the hardware.

    ```python
    # File: subsystems/communicate.py (Simplified 'when_aiming_refreshes')
    # ... imports ...
    from toolbox.globals import runtime # Import runtime

    def when_aiming_refreshes():
        # Get the aiming results FROM runtime
        target_3d = runtime.aiming.target_3d
        target_status = runtime.aiming.target_status
        
        if target_3d is None:
            # Send "no target" message
            message_to_embedded.X = 0.0 
            # ...
        else:
            # Send the actual coordinates
            message_to_embedded.X = float(target_3d[0])
            # ...
        message_to_embedded.status = target_status.value
        
        # ... send the message_to_embedded over serial port ...
    ```
    This subsystem reads the `runtime.aiming.target_3d` calculated by the [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md) and uses it to prepare the command sent to the physical robot.

*   **Logging Subsystem (`log.py`)**: Reads various pieces of data from `runtime` to record what happened in the frame.

    ```python
    # File: subsystems/log.py (Simplified 'when_finished_processing_frame')
    # ... imports ...
    from toolbox.globals import runtime # Import runtime

    def when_finished_processing_frame():
        # Get lots of data FROM runtime for logging
        frame_number = runtime.frame_number
        color_image = runtime.color_image
        bounding_boxes = runtime.modeling.bounding_boxes
        target_3d = runtime.aiming.target_3d
        status = runtime.aiming.target_status
        # ... calculate FPS ...

        print(f'frame#:{frame_number}, targets={len(bounding_boxes)} ...')

        if display_live_frames:
            # Use the data to draw boxes on the image for display
            image = generate_image(...) # This helper function uses runtime data
            image.show()
            
        if save_frame_to_file:
            # Save the image from runtime to a video file
            color_video_writer.add_frame(runtime.color_image)
    ```
    The [Logging Subsystem (`log`)](09_logging_subsystem___log___.md) reads many different values from `runtime` (like `frame_number`, `color_image`, `bounding_boxes`, `target_3d`, `status`) to print summaries, display visuals, and save videos.

## The Journey of Data Through `runtime` (One Frame)

Let's visualize how data flows via `runtime` for a single frame:

```mermaid
sequenceDiagram
    participant Loop as Main Loop
    participant VS as Video Stream
    participant RT as runtime (Blackboard)
    participant Mod as Model
    participant Aim as Aiming
    participant Comm as Communicate
    participant Log as Logging

    Loop->>VS: Get next frame data
    VS-->>RT: Write frame_number, color_image, depth_image
    Loop->>Mod: Process frame
    Mod->>RT: Read color_image
    Mod-->>RT: Write modeling.bounding_boxes, modeling.enemy_boxes
    Loop->>Aim: Calculate aim
    Aim->>RT: Read modeling.enemy_boxes
    Aim-->>RT: Write aiming.target_3d, aiming.target_status
    Loop->>Comm: Send commands
    Comm->>RT: Read aiming.target_3d, aiming.target_status
    Comm-->>Loop: (Sends command to hardware)
    Loop->>Log: Record frame
    Log->>RT: Read frame_number, color_image, modeling.*, aiming.*
    Log-->>Loop: (Prints log, saves video frame)
```

This diagram shows `runtime` acting as the central exchange. Subsystems write their outputs to it, and subsequent subsystems read the inputs they need from it.

## Where is `runtime` Created?

Just like `config`, the `runtime` object is created once when the program starts and made globally available. This happens in the `toolbox/globals.py` file.

```python
# File: toolbox/globals.py (Simplified)

# ... imports ...
from super_map import LazyDict # The type used for runtime

# --- Configuration Loading ---
# ... code to load 'config' from info.yaml ...
config = info.config
# ... path variables ...

# --- Shared Runtime Data ---
# Create an empty, flexible dictionary for temporary data
runtime = LazyDict()

# --- Other Globals ---
# ... print function setup ...
```

This simple line `runtime = LazyDict()` creates the empty blackboard, ready for the subsystems to start writing on it as the [Main Execution Loop](01_main_execution_loop_.md) begins. Because it's defined here in `toolbox/globals.py`, any other file can simply `from toolbox.globals import runtime` to get access to the same shared object.

## `runtime` vs. `config` Recap

It's important to remember the difference:

*   **`config`**: Holds **settings** and **parameters**. Loaded from `info.yaml` at the start. Changes **rarely** (only if you edit the file and restart). Think: *Instruction Manual*.
*   **`runtime`**: Holds **temporary data** specific to the **current frame** being processed. Changes **constantly** (every few milliseconds). Think: *Shared Blackboard / Message Board*.

## Conclusion

The **Shared Runtime Data (`runtime`)** object is the communication hub for data that changes *during* the processing of each camera frame. It acts like a shared blackboard where subsystems like the camera interface, model detector, and aimer can leave information (like the current image, found targets, aiming points) for each other to pick up almost instantly.

Implemented as a flexible `LazyDict` and made globally accessible, `runtime` allows different parts of our auto-aim system to cooperate efficiently within the tight time constraints of the [Main Execution Loop](01_main_execution_loop_.md). It ensures that the aiming calculations are based on the targets found in the very same frame, keeping the system responsive.

Now that we understand the main loop, configuration, and the runtime data exchange, let's start looking at the individual subsystems in more detail. We'll begin with the first station on our assembly line: the system that actually gets the images from the camera.

Next: [Chapter 4: Video Stream Subsystem](04_video_stream_subsystem_.md)

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)