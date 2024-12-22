from toolbox.globals import runtime, config
from toolbox.geometry_tools import BoundingBox

# import frame
R_FRAME = runtime.color_image

def paper_detector():
    
    # your algorithm should output a top left corner and bottom right corner
    # then we use these to corners to instantiate a BoundingBox object
    
    box = BoundingBox.from_points(top_left=(x1, y1), bottom_right=(x2, y2))
    
    # export bbox
    runtime.modeling.bounding_box = box
    pass
    