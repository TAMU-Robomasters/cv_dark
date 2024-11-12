import json
from time import time as now
from datetime import datetime as dt

from toolbox.globals import path_to, config, print, runtime, absolute_path_to
from toolbox.video_tools import Video, VideoWriter
from toolbox.image_tools import Image, rgb
from toolbox.cold_storage import ColdStorage
from subsystems.aim import TargetStatus
from subsystems.video_stream import video_stream


# 
# config
# 
display_live_frames       = config.log.display_live_frames
save_frame_to_file        = config.log.save_frame_to_file
display_kf_prediction     = config.log.display_kf_prediction
save_depth                = config.log.save_depth
save_rate                 = config.log.save_rate
record_video_output_color = absolute_path_to.record_video_output_color
video_output              = absolute_path_to.video_output
camera                    = config.hardware.camera
depth_compatible          = config.hardware.camera_has_depth
should_benchmark          = config.mode == 'benchmark'

# create incremented storage path
timestamp = dt.now()
video_stamp = timestamp.strftime("%m%d%y-%H:%M")
video_color_output_path = f'{absolute_path_to.record_video_output_color}-{video_stamp}.color.ignore.mp4'
video_depth_output_path = None
if depth_compatible and save_depth:
    video_depth_output_path = f'{absolute_path_to.record_video_output_color}-{video_stamp}.depth.ignore.mp4'

color_video_writer = VideoWriter(save_to=video_color_output_path, fps=config.log.estimated_framerate)
depth_video_writer = VideoWriter(save_to=video_depth_output_path, fps=config.log.estimated_framerate) if video_depth_output_path else None

# 
# 
# main
# 
# 
runtime.prev_loop_time = int(now() * 1000) # init time value
runtime.total_fps = 0
def when_finished_processing_frame():
    global color_video_writer
    global depth_video_writer
    
    # import data
    frame_number       = runtime.frame_number
    color_image        = runtime.color_image
    depth_image        = runtime.depth_image
    prev_loop_time     = runtime.prev_loop_time
    bounding_boxes     = runtime.modeling.bounding_boxes
    
    # 
    # compute loop time
    # 
    now_in_miliseconds = int(now() * 1000)
    iteration_time = now_in_miliseconds-prev_loop_time
    runtime.total_fps += (1000/(iteration_time))
    runtime.prev_loop_time = now_in_miliseconds    
    # 
    # print
    # 
    print(f'\nframe#:{f"{frame_number}".rjust(5)},{f"{iteration_time}".rjust(4)}ms, FPS:{f"{1000//iteration_time}".rjust(3)}, targets={len(bounding_boxes)} ', sep='', end='', flush=True)
    
    # 
    # handle image
    # 
    should_save_frame = (save_frame_to_file and (frame_number % save_rate == 0))
    if display_live_frames or should_save_frame:
        image = generate_image(1000/iteration_time)
    
    if display_live_frames:
        image.show()
    
    if should_save_frame:
        color_video_writer.add_frame(runtime.color_image)
        
        if depth_compatible and save_depth:
            # FIXME: this probably wont work as-is because
            # depth images are z16 video/image format instead of rbg8
            # the fix would be to convert the numpy array into an array that looks like a grayscale image
            # I think the z16 pixels are floats, so they would need to be multiplied by, idk 100, and then converted to ints
            depth_video_writer.add_frame(runtime.depth_image)

    if should_benchmark and runtime.frame_number == config.stop_after:
        print("\nBenchmark Complete")
        when_iteration_stops()
        exit()

def when_iteration_stops():
    # NOTE: this function might get run a couple times at exit (main.py calls it)
    avg_fps = runtime.total_fps / runtime.get("frame_number", 1)
    print(f"\naverage FPS: {avg_fps:.2f}")
    if save_frame_to_file:
        color_video_writer.save()
        if save_depth and depth_video_writer:
            depth_video_writer.save()
# 
# disable log check
# 
if config.log.disable_all_logging:
    # override above definition and disable
    def when_finished_processing_frame():
        pass # do nothing intentionally

# 
# 
# helpers
# 
# 
def visualize_depth_frame(depth_frame_array):
    """
    Displays a depth frame in a visualized color format.

    Input: Depth Frame.
    Output: None.
    """
    import cv2
    depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_frame_array, alpha = 0.04), cv2.COLORMAP_JET)# this puts a color efffect on the depth frame
    images = depth_colormap                              # use this for individual streams
    cv2.namedWindow('Align Example', cv2.WINDOW_NORMAL)   # names and shows the streams
    cv2.imwrite('depthmap.jpg', images)

    # # if you press escape or q you can cancel the process
    key = cv2.waitKey(1)
    print("press escape to cancel")
    if key & 0xFF == ord('q') or key == 27:
        cv2.destroyAllWindows()


def generate_image(fps=0):
    color_image             = runtime.color_image
    bounding_boxes          = runtime.modeling.bounding_boxes
    enemy_boxes             = runtime.modeling.enemy_boxes
    current_confidence      = runtime.aiming.current_confidence
    best_bounding_box       = runtime.aiming.best_bounding_box
    center_point            = runtime.aiming.center_point
    center_point_prediction = runtime.aiming.center_point_prediction
    target_3d               = runtime.aiming.target_3d
    target_3d_prediction    = runtime.aiming.target_3d_prediction
    status                  = runtime.aiming.target_status
    
    image = Image(runtime.color_image)

    if len(bounding_boxes) > 0:
        white  = rgb(255, 255, 255)
        red    = rgb(240, 113, 120)
        blue   = rgb(130, 170, 255)
        cyan   = rgb(137, 221, 255)
        green  = rgb(195, 232, 141)
        yellow = rgb(254, 195,  85)
        for each in bounding_boxes:
            image.add_bounding_box(each, color=rgb(255, 255, 255))
        for each in enemy_boxes:
            image.add_bounding_box(each, color=rgb(254, 195,  85))
        if status == TargetStatus.TARGET_FOUND:
            image.add_bounding_box(best_bounding_box, color=rgb(240, 113, 120))
            image.add_point(x=center_point.x     , y=center_point.y     , color=rgb(130, 170, 255), radius=10)
        if display_kf_prediction:
            if depth_compatible:
                target_3d_pixel = video_stream.point3d_to_pixel(target_3d_prediction)
                image.add_point(x=target_3d_pixel[0]    , y=target_3d_pixel[1]     , color=green, radius=10)
            else:
                image.add_point(x=center_point_prediction.x     , y=center_point_prediction.y     , color=green, radius=10)
    
    x_location = 30
    y_location = 50
    if depth_compatible:
        disp_target_3d = [round(x, 3) for x in target_3d] if target_3d else ["NAN, NAN, NAN"]
        image.add_text(text=f"target_3d: {    disp_target_3d         }", location=(x_location, y_location)); y_location += 50
    image.add_text(text=f"confidence: {       current_confidence :.2f}", location=(x_location, y_location)); y_location += 50
    image.add_text(text=f"status: {           status.name            }", location=(x_location, y_location)); y_location += 50
    image.add_text(text=f"fps: {              fps                :.2f}", location=(x_location, y_location)); y_location += 50
        
    return image
