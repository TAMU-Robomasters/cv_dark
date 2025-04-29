# Chapter 9: Logging Subsystem (`log`)

Welcome to the final chapter! In the [previous chapter](08_communication_subsystem___communicate___.md), we saw how the [Communication Subsystem (`communicate`)](08_communication_subsystem___communicate___.md) acts as the system's voice, sending the final aiming commands to the robot's hardware. We've followed the entire process from seeing an image to aiming the robot.

But how do we know if everything worked correctly? How fast is the system running? What did the robot actually see? What aiming commands were sent? If something goes wrong, how can we figure out what happened?

## The Problem: Flying Blind

Imagine flying an airplane without any instruments on the dashboard. You wouldn't know your speed, altitude, or if the engines are working correctly! Running our auto-aim system without feedback is similar. We need a way to monitor its performance, see what it's doing, and record information for later analysis or debugging.

We need answers to questions like:
*   Is the system running fast enough (Frames Per Second - FPS)?
*   Did the [Model Subsystem](05_model_subsystem_.md) detect any targets in the last frame?
*   Where did the [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md) decide to point?
*   Can we see what the camera sees, with the detected targets highlighted?
*   Can we save a recording of the processed video to review later?

## The Solution: `log` - The Dashboard and Flight Recorder

The **Logging Subsystem (`log`)** is designed to be the system's dashboard and flight recorder. It handles all the tasks related to recording what's happening and visualizing it for us.

Think of `log` as the control panel and recording device for our auto-aim system. Its main jobs include:

1.  **Displaying Live Video:** It can show a window with the live camera feed. Crucially, it can draw information on top of this video, like the [BoundingBox](06_boundingbox_.md)es found by the model, the calculated aiming point, and status text. This gives us immediate visual feedback.
2.  **Saving Processed Video:** It can save the frames (with the visual overlays) to a video file on the disk. This is like a flight recorder, storing data for later review, debugging, or creating demos.
3.  **Printing Statistics:** It prints useful information to the console (the text window where you run the program), like the current FPS, the number of targets detected, and the status of the aiming system for each frame.
4.  **Managing Benchmarks:** For performance testing ("benchmarking"), it can help manage the run and report results.

## How the Main Loop Uses `log`

The `log` subsystem is the final step inside the [Main Execution Loop](01_main_execution_loop_.md) for each frame. After all the other subsystems have done their work (getting the image, finding targets, calculating aim, sending commands), the loop asks `log` to record and display what happened.

```python
# File: main.py (Simplified loop)

from subsystems import video_stream, model, aim, communicate, log # Import!
from toolbox.globals import runtime

# ... (loop starts, video_stream gets frame) ...
for runtime.frame_number, runtime.color_image, runtime.depth_image in video_stream.frames():

    # 1. Model finds targets
    model.when_frame_arrives()

    # 2. Aim calculates 3D point
    aim.when_bounding_boxes_refresh()

    # 3. Communicate sends command
    communicate.when_aiming_refreshes()

    # ---> 4. Log records and displays info for this frame <---
    log.when_finished_processing_frame()

# ... (loop ends, cleanup happens) ...
```

The call `log.when_finished_processing_frame()` tells the Logging Subsystem: "Okay, the processing for this frame is done. Now, do your logging magic!"

Let's look inside `log.when_finished_processing_frame()` (in `subsystems/log.py`) to see what kind of magic it performs.

## Key Features of the Logging Subsystem

The `log` subsystem performs several tasks, often controlled by settings in the [Global Configuration (`config`)](02_global_configuration___config___.md).

**1. Printing Statistics (like FPS)**

One of the simplest but most useful things `log` does is calculate and print how long the last frame took to process and the resulting Frames Per Second (FPS).

```python
# File: subsystems/log.py (Simplified stats calculation)
from time import time as now
from toolbox.globals import runtime, print

# Initialize runtime.prev_loop_time before the loop starts
# runtime.prev_loop_time = int(now() * 1000)

def when_finished_processing_frame():
    # Get data needed from runtime
    frame_number   = runtime.frame_number
    prev_loop_time = runtime.prev_loop_time # Time when previous frame ended
    bounding_boxes = runtime.modeling.bounding_boxes # How many targets total

    # Calculate time taken for this frame
    now_ms = int(now() * 1000)
    iteration_time_ms = now_ms - prev_loop_time
    current_fps = 1000 // iteration_time_ms if iteration_time_ms > 0 else 0
    
    # Update total FPS for averaging later
    runtime.total_fps += current_fps
    
    # Store current time for the *next* frame's calculation
    runtime.prev_loop_time = now_ms

    # Print the stats to the console
    print(f'frame#:{frame_number}, {iteration_time_ms}ms, FPS:{current_fps}, targets={len(bounding_boxes)}')
    
    # ... other logging tasks (displaying, saving) ...
```

*   It reads the `frame_number` and the time the *last* frame finished (`prev_loop_time`) from the [Shared Runtime Data (`runtime`)](03_shared_runtime_data___runtime___.md).
*   It calculates how many milliseconds (`iteration_time_ms`) passed since the last frame finished.
*   It calculates the current `fps` (approximately 1000 / milliseconds).
*   It updates a running total `runtime.total_fps` to calculate an average later.
*   It saves the current time (`now_ms`) into `runtime.prev_loop_time` so the *next* iteration can use it.
*   Finally, it uses `print()` to display the frame number, time taken, current FPS, and the number of targets found in this cycle. This gives you real-time feedback in your terminal.

**2. Displaying Live Video with Overlays**

If you set `display_live_frames: true` in your `info.yaml` configuration file, the `log` subsystem will open a window showing the live video feed. More importantly, it draws helpful information on top!

```python
# File: subsystems/log.py (Simplified display logic)
from toolbox.globals import runtime, config
from toolbox.image_tools import Image, rgb # Helper for image operations

# Check config setting (runs once at start)
display_live_frames = config.log.display_live_frames 

def when_finished_processing_frame():
    # ... (calculate stats) ...

    # Only generate and show image if configured to do so
    if display_live_frames:
        # Call a helper function to create the image with drawings
        image_with_overlays = generate_image(fps=current_fps) # Pass FPS for display
        # Show the image in a window
        image_with_overlays.show() # Uses OpenCV's imshow() behind the scenes

    # ... (saving logic) ...

def generate_image(fps=0):
    """Helper to draw info onto the frame."""
    # Get data from runtime needed for drawing
    color_image       = runtime.color_image
    bounding_boxes    = runtime.modeling.bounding_boxes # All boxes
    enemy_boxes       = runtime.modeling.enemy_boxes    # Just enemy boxes
    best_bounding_box = runtime.modeling.best_bounding_box # The one chosen by aim
    center_point      = runtime.aiming.center_point      # Center of best box
    target_3d         = runtime.aiming.target_3d         # Aiming coordinate
    status            = runtime.aiming.target_status     # Aiming status

    # Create an Image object (wrapper around the raw image data)
    image = Image(color_image) 

    # Draw all detected boxes (e.g., in white)
    for box in bounding_boxes:
        image.add_bounding_box(box, color=rgb(255, 255, 255))
    
    # Draw enemy boxes (e.g., in yellow)
    for box in enemy_boxes:
        image.add_bounding_box(box, color=rgb(254, 195, 85)) # Yellow

    # Highlight the best box (e.g., in red) and its center
    if best_bounding_box:
        image.add_bounding_box(best_bounding_box, color=rgb(240, 113, 120)) # Red
        image.add_point(x=center_point.x, y=center_point.y, color=rgb(130, 170, 255), radius=5) # Blue dot

    # Add text information (FPS, Status, 3D Coords)
    y_location = 50 # Starting vertical position for text
    image.add_text(text=f"FPS: {fps:.2f}", location=(30, y_location)); y_location += 30
    image.add_text(text=f"Status: {status.name}", location=(30, y_location)); y_location += 30
    if target_3d:
        coords = f"({target_3d[0]:.2f}, {target_3d[1]:.2f}, {target_3d[2]:.2f})"
        image.add_text(text=f"Aim (X,Y,Z): {coords}", location=(30, y_location)); y_location += 30
    
    return image # Return the modified image object
```

*   It checks the `config.log.display_live_frames` setting.
*   If true, it calls a helper function `generate_image()`.
*   `generate_image()` reads various pieces of data from `runtime` (the image itself, the lists of boxes, the chosen box, the aim point, status, etc.).
*   It uses helper functions from `toolbox.image_tools` (like `Image()`, `add_bounding_box()`, `add_point()`, `add_text()`) to draw rectangles, dots, and text onto a copy of the image. Different colors can be used for different types of boxes.
*   The main function then calls `.show()` on the resulting image, which displays it in a window on your screen.

**3. Saving Processed Video**

Similar to displaying live frames, if `save_frame_to_file: true` is set in `config`, the `log` subsystem will save the processed video feed to a file.

```python
# File: subsystems/log.py (Simplified saving logic)
from toolbox.globals import runtime, config, absolute_path_to
from toolbox.video_tools import VideoWriter # Helper for writing video files
from datetime import datetime as dt

# Check config setting (runs once at start)
save_frame_to_file = config.log.save_frame_to_file

# Setup video writer object (runs once at start)
color_video_writer = None
if save_frame_to_file:
    timestamp = dt.now().strftime("%m%d%y-%H%M") # Create unique filename
    video_path = f'{absolute_path_to.record_video_output_color}-{timestamp}.color.ignore.mp4'
    estimated_fps = config.log.estimated_framerate # Use configured FPS for saving
    color_video_writer = VideoWriter(save_to=video_path, fps=estimated_fps)
    print(f"[Log] Saving video enabled: {video_path}")

def when_finished_processing_frame():
    # ... (calculate stats) ...
    # ... (display logic) ...

    # Save frame if configured AND the writer exists
    if save_frame_to_file and color_video_writer:
        # Add the *original* color image to the video file
        # (Could also save the 'image_with_overlays' if needed)
        color_video_writer.add_frame(runtime.color_image) 
        
    # Optionally save depth video too (more complex, needs format conversion)
    # if config.log.save_depth and depth_video_writer:
    #     processed_depth = process_depth_for_video(runtime.depth_image)
    #     depth_video_writer.add_frame(processed_depth)

    # ... (benchmark check) ...
```

*   It checks `config.log.save_frame_to_file`.
*   If true, it creates a `VideoWriter` object when the program starts. This object knows the output filename (using `absolute_path_to` from `config` and adding a timestamp) and the desired FPS for the saved video (from `config.log.estimated_framerate`).
*   Inside `when_finished_processing_frame`, if saving is enabled, it calls `color_video_writer.add_frame(runtime.color_image)`. This passes the current frame's image data to the `VideoWriter`.
*   The `VideoWriter` object (from `toolbox.video_tools`) handles the complexities of encoding the sequence of frames into a standard video format (like MP4) and writing it to the disk.

**4. Cleanup (`when_iteration_stops`)**

What happens when the program stops (e.g., you press Ctrl+C, or a benchmark finishes)? If we were saving a video, we need to make sure the video file is properly finalized and closed. Otherwise, the file might be corrupted!

This is handled by the `when_iteration_stops` function, which is registered to run automatically when the program exits.

```python
# File: main.py (Registering the cleanup function)
import atexit
from subsystems import log
# ... other imports ...

# Tell Python to call log.when_iteration_stops when the program exits
atexit.register(log.when_iteration_stops) 

# ... main loop ...

# Call it explicitly if the loop finishes normally (less common)
log.when_iteration_stops() 
```

```python
# File: subsystems/log.py (The cleanup function itself)
from toolbox.globals import runtime, print

# Assumes 'color_video_writer' and potentially 'depth_video_writer' exist

def when_iteration_stops():
    # Calculate and print the final average FPS
    avg_fps = runtime.total_fps / runtime.get("frame_number", 1)
    print(f"\nAverage FPS: {avg_fps:.2f}")

    # Tell the video writers to finish saving their files
    if save_frame_to_file: # Check if saving was ever enabled
        if color_video_writer:
            color_video_writer.save() # This finalizes the video file
        # if save_depth and depth_video_writer:
        #     depth_video_writer.save()
```

*   The `atexit.register(log.when_iteration_stops)` line in `main.py` ensures that the `log.when_iteration_stops` function gets called automatically before the program fully closes.
*   Inside `when_iteration_stops`, it first prints the final average FPS calculated over the whole run.
*   Most importantly, if video saving was enabled, it calls the `.save()` method on the `VideoWriter` object(s). This crucial step tells the writer to finalize the video encoding, write any remaining buffered data, and properly close the output file.

## Under the Hood: Putting it All Together

The `log` subsystem acts as a central hub for observation and recording. It doesn't perform core logic like detection or aiming, but it relies heavily on the results produced by other subsystems and the settings provided.

**Workflow:**

1.  **Trigger:** Called by the [Main Execution Loop](01_main_execution_loop_.md) via `when_finished_processing_frame()`.
2.  **Gather Data:** Reads various pieces of information from the [Shared Runtime Data (`runtime`)](03_shared_runtime_data___runtime___.md) blackboard (current frame, boxes, aim point, status, timing info).
3.  **Check Configuration:** Reads settings from the [Global Configuration (`config`)](02_global_configuration___config___.md) (`display_live_frames`, `save_frame_to_file`, `save_rate`, etc.) to determine what actions to perform.
4.  **Process & Output:**
    *   Calculates and `print`s stats (FPS, etc.) to the console.
    *   If configured, calls `generate_image` (using `toolbox.image_tools`) to create the visual overlay, then calls `.show()` to display it.
    *   If configured, calls `.add_frame()` on the appropriate `VideoWriter` object (using `toolbox.video_tools`) to save the frame.
5.  **Cleanup (on Exit):** The separate `when_iteration_stops` function is called to finalize video files via `VideoWriter.save()`.

**Simplified Sequence Diagram:**

```mermaid
sequenceDiagram
    participant Loop as Main Loop
    participant Log as Logging Subsystem (log)
    participant RT as runtime Blackboard
    participant Cfg as config Settings
    participant ImgTool as Image Tools
    participant VidTool as Video Tools
    participant Output as Console/Screen/File

    Loop->>Log: Call when_finished_processing_frame()
    Log->>RT: Read frame_number, image, boxes, aim, status, time
    Log->>Cfg: Read display_live_frames?, save_frame_to_file?
    Log->>Output: Print Stats (Console)
    alt Display Enabled
        Log->>ImgTool: generate_image(runtime data)
        ImgTool-->>Log: Image with Overlays
        Log->>Output: image.show() (Screen)
    end
    alt Save Enabled
        Log->>VidTool: video_writer.add_frame(image)
        VidTool->>Output: Writes to video file (File)
    end
    Log-->>Loop: Done for this frame
    
    Note over Loop, Log: Later, on program exit...
    Loop->>Log: Call when_iteration_stops() (via atexit)
    Log->>RT: Read total_fps, frame_number
    Log->>Output: Print Average FPS (Console)
    alt Save Enabled
        Log->>VidTool: video_writer.save()
        VidTool->>Output: Finalizes video file (File)
    end
```

## Conclusion

The **Logging Subsystem (`log`)** is the indispensable dashboard and flight recorder for our auto-aim system. It provides crucial visibility into the system's operation by displaying live, annotated video feeds, saving processed video for later analysis, and printing real-time performance statistics like FPS.

By reading data from the [Shared Runtime Data (`runtime`)](03_shared_runtime_data___runtime___.md) and using settings from the [Global Configuration (`config`)](02_global_configuration___config___.md), `log` gives us the tools we need to monitor, debug, and understand how all the other subsystems – [Video Stream](04_video_stream_subsystem_.md), [Model](05_model_subsystem_.md), [Aiming](07_aiming_subsystem___aim___.md), and [Communication](08_communication_subsystem___communicate___.md) – are working together within the [Main Execution Loop](01_main_execution_loop_.md).

This concludes our tour through the major components of the auto-aim project! We hope these chapters have given you a clear, beginner-friendly understanding of how each piece contributes to the overall goal. Happy coding!

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)