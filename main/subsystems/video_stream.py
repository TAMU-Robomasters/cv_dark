from toolbox.globals import path_to, config, print
from toolbox.image_tools import Image
from toolbox.camera_threader import CameraThreader

# 
# select which file to import from
# 
if config.hardware.camera == 'zed':
    from subsystems.video_streaming.zed import VideoStream
elif config.hardware.camera == 'realsense':
    from subsystems.video_streaming.realsense import VideoStream
else:
    from subsystems.video_streaming.simulation import VideoStream

vid_source = VideoStream()
vid_threader = CameraThreader(vid_source)
# frames = vid_source.frames
frames = vid_threader.frames
# vid_threader.start()