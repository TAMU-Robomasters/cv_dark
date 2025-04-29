# Chapter 6: BoundingBox

In the [previous chapter](05_model_subsystem_.md), we learned how the [Model Subsystem](05_model_subsystem_.md) acts like the robot's vision brain, analyzing camera images to find potential enemy robots. We saw that when it finds an object, it tells us *where* it is in the image. But how exactly does it communicate that location?

## The Problem: Pointing Things Out in an Image

Imagine you're looking at a photo with several people, and you want to tell your friend exactly which person you're talking about. You could try describing them ("the person in the red shirt near the back"), but that can be slow and ambiguous. A much simpler way is to just draw a box around them!

Our auto-aim system faces the same problem. The [Model Subsystem](05_model_subsystem_.md) detects an enemy robot in the camera image (which is just a grid of pixels). It needs a clear, simple, and standard way to tell other parts of the system, like the [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md), exactly where that robot is located within the 2D image.

## The Solution: `BoundingBox` - Drawing a Box Around It

The **`BoundingBox`** is our standard way of doing this. It's a fundamental data structure that represents a simple **rectangle** in the image.

*   **Think of it:** Literally drawing a rectangular box around the detected object in the picture.
*   **Its Purpose:** To clearly mark the location and extent of an object within the 2D image frame.

This `BoundingBox` gives us all the information needed to know the object's position and approximate size in the image.

## How a `BoundingBox` is Defined

To draw a rectangle, you need a few key pieces of information. Our `BoundingBox` stores these:

1.  **Top-Left Corner:** Where does the box start? We need the **x** (horizontal) and **y** (vertical) coordinates of the top-left corner pixel.
    *   Remember: In computer images, (0, 0) is usually the **top-left** corner of the entire image.
    *   The x-coordinate increases as you go right.
    *   The y-coordinate increases as you go *down*.
2.  **Size:** How big is the box? We need its **width** (how far it extends horizontally) and **height** (how far it extends vertically).

So, a `BoundingBox` is defined by four numbers: `x_top_left`, `y_top_left`, `width`, and `height`.

```
Image Coordinate System:
(0,0) --> x increases
  |
  v y increases

A Bounding Box:
(x_top_left, y_top_left) *-------+
                         |       | height
                         |       |
                         +-------* (x_top_left + width, y_top_left + height)
                            width
```

## Using `BoundingBox` in the Code

The [Model Subsystem](05_model_subsystem_.md) is the primary *producer* of `BoundingBox` objects. When it runs its detection algorithm (like YOLOv8), the results often come in a format that includes these four values for each detected object. Our code then packages this information into a `BoundingBox` object.

Let's see how we might create and use one. The `BoundingBox` class lives in the `toolbox/geometry_tools.py` file.

```python
# Import the BoundingBox class
from toolbox.geometry_tools import BoundingBox

# Imagine the model detected a robot with these coordinates:
# Top-left corner at x=100, y=50
# Width = 80 pixels, Height = 120 pixels
detected_x = 100
detected_y = 50
detected_width = 80
detected_height = 120

# Create a BoundingBox object
robot_box = BoundingBox([detected_x, detected_y, detected_width, detected_height])

# Now we can easily access its properties:
print(f"Box starts at X: {robot_box.x_top_left}") # Output: Box starts at X: 100
print(f"Box starts at Y: {robot_box.y_top_left}") # Output: Box starts at Y: 50
print(f"Box width: {robot_box.width}")         # Output: Box width: 80
print(f"Box height: {robot_box.height}")        # Output: Box height: 120
```

This `robot_box` object now neatly contains all the information about where the robot is in the 2D image. The [Model Subsystem](05_model_subsystem_.md) puts a list of these `BoundingBox` objects (one for each detected enemy) into `runtime.modeling.enemy_boxes`, where other subsystems can find them.

For example, the [Logging Subsystem (`log`)](09_logging_subsystem___log___.md) uses these boxes to draw rectangles on the video feed you see when `display_live_frames` is enabled in the [Global Configuration (`config`)](02_global_configuration___config___.md).

```python
# File: subsystems/log.py (Simplified drawing part)
from toolbox.image_tools import Image, rgb # For drawing
from toolbox.globals import runtime

def generate_image(fps=0):
    # ... get other data from runtime ...
    enemy_boxes = runtime.modeling.enemy_boxes # Get the list of boxes
    image_to_draw_on = Image(runtime.color_image) # Make an Image object

    # Draw each enemy box onto the image
    box_color = rgb(254, 195, 85) # Yellow
    for box in enemy_boxes:
        image_to_draw_on.add_bounding_box(box, color=box_color)

    # ... add text, maybe draw the best box in a different color ...
    return image_to_draw_on
```

## Helpful Features: Center and Area

Just knowing the corner and size is useful, but often we need derived information. The `BoundingBox` class includes helpful built-in calculations:

*   **`.center`**: Calculates the exact center point (x, y) of the bounding box. This is very useful for the [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md) to know where the middle of the target is.
*   **`.area`**: Calculates the area of the box (width * height). This can give a rough idea of how large the object appears in the image, which might correlate with distance.

```python
# Continuing from the previous example:
robot_box = BoundingBox([100, 50, 80, 120])

# Get the center point
center_coords = robot_box.center
print(f"Center X: {center_coords.x}") # Output: Center X: 140.0 (100 + 80/2)
print(f"Center Y: {center_coords.y}") # Output: Center Y: 110.0 (50 + 120/2)

# Get the area
box_area = robot_box.area
print(f"Area: {box_area}")           # Output: Area: 9600.0 (80 * 120)
```

The [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md) uses the `.center` property extensively when deciding where to point. It might also use `.width`, `.height`, or `.area` as part of its logic to choose the best target if multiple enemies are detected.

## A Peek Inside the Code (`toolbox/geometry_tools.py`)

Let's look at a simplified version of how the `BoundingBox` class is defined in `toolbox/geometry_tools.py`.

```python
# File: toolbox/geometry_tools.py (Simplified BoundingBox class)
import numpy as np # Used for math operations

# We also use Position, which is a simple list wrapper for coordinates
class Position(list):
    @property
    def x(self): return self[0]
    # ... other properties like y, z ...

class BoundingBox(list):
    """
    Represents a box using: x_top_left, y_top_left, width, height format
    It inherits from 'list', so the data is stored like [x, y, w, h].
    """

    # --- Direct Properties ---
    # These use '@property' to make accessing list elements easier

    @property
    def x_top_left(self): return self[0] # Gets the first item in the list

    @property
    def y_top_left(self): return self[1] # Gets the second item

    @property
    def width(self): return self[2] # Gets the third item

    @property
    def height(self): return self[3] # Gets the fourth item

    # --- Calculated Properties ---
    # These perform calculations on the fly

    @property
    def center(self):
        """Calculates the center point."""
        center_x = self.x_top_left + (self.width / 2)
        center_y = self.y_top_left + (self.height / 2)
        # Returns a Position object holding [center_x, center_y]
        return Position([center_x, center_y])

    @property
    def area(self):
        """Calculates the area."""
        return self.width * self.height

    # ... other methods like from_points, contains, __repr__ ...
```

**Key things to notice:**

1.  **`class BoundingBox(list):`**: It's actually built on top of a standard Python `list`. When you create `BoundingBox([100, 50, 80, 120])`, you're creating a list with those four numbers.
2.  **`@property`**: This is a Python trick (called a decorator). It makes a function look like a simple variable. When you access `robot_box.x_top_left`, Python automatically calls the `x_top_left(self)` function, which returns the first element (`self[0]`) of the underlying list. This makes the code cleaner to read and write!
3.  **Calculated Properties:** Properties like `center` and `area` aren't stored directly. They perform a quick calculation using the stored `x_top_left`, `y_top_left`, `width`, and `height` whenever you access them. This ensures they are always up-to-date without needing extra storage.

## Conclusion

The **`BoundingBox`** is a simple yet essential data structure in our auto-aim project. It provides a standard way to represent the location and size of a detected object within a 2D image using its top-left corner coordinates (`x_top_left`, `y_top_left`) and its dimensions (`width`, `height`).

Generated primarily by the [Model Subsystem](05_model_subsystem_.md), `BoundingBox` objects are stored in the [Shared Runtime Data (`runtime`)](03_shared_runtime_data___runtime___.md) and used by other parts of the system. Its helpful properties like `.center` and `.area` make it easy for subsystems like [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md) and [Logging Subsystem (`log`)](09_logging_subsystem___log___.md) to understand and utilize the detection results effectively.

Now that we know how objects are located in the 2D image using `BoundingBox`, how do we use that information, potentially along with depth data, to figure out where to point the robot's turret or gimbal in 3D space? That's the job of the next subsystem we'll explore.

Next: [Chapter 7: Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md)

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)