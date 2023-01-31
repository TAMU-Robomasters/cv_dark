import json
from time import time as now

from toolbox.globals import path_to, config, print, runtime, absolute_path_to
from toolbox.video_tools import Video
from toolbox.image_tools import Image, rgb
from toolbox.pickle_tools import large_pickle_save

# 
# config
# 
display_live_frames       = config.log.display_live_frames
save_frame_to_file        = config.log.save_frame_to_file
save_rate                 = config.log.save_rate
save_to_disk_after        = config.log.save_to_disk_after
record_video_output_color = absolute_path_to.record_video_output_color
video_output              = absolute_path_to.video_output
max_number_of_frames      = config.log.max_number_of_frames
camera                    = config.hardware.camera

# 
# init
# 
video_depth_output_path = None
video_color_output_path = video_output

color_frames = []
depth_frames = []

# read json
with open(absolute_path_to.permanent_storage, 'r') as in_file:
    permanent_storage = json.load(in_file)
# increment
permanent_storage["video_count"] += 1
# write json
with open(absolute_path_to.permanent_storage, 'w') as outfile:
    json.dump(permanent_storage, outfile)

# create incremented storage path
video_count = permanent_storage["video_count"]
video_color_output_path = f'{absolute_path_to.record_video_output_color}{video_count}.ignore.mp4'
video_depth_output_path = f'{absolute_path_to.record_video_output_color}{video_count}.depth.ignore.pickle'

# 
# 
# main
# 
# 
runtime.prev_loop_time = 0 # init time value
def when_finished_processing_frame():
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
    runtime.prev_loop_time = now_in_miliseconds
    
    # 
    # print
    # 
    print(f'\nframe#:{f"{frame_number}".rjust(5)},{f"{iteration_time}".rjust(4)}ms, FPS:{f"{1000//iteration_time}".rjust(3)}, targets={len(bounding_boxes)} ', sep='', end='', flush=True)
    
    # 
    # handle image
    # 
    if display_live_frames or (save_frame_to_file and (frame_number % save_rate == 0)):
        image = generate_image(1000/iteration_time)
    
    if display_live_frames:
        image.show()
    
    if (save_frame_to_file and (frame_number % save_rate == 0)):
        global color_frames
        global depth_frames
        color_frames.append(runtime.color_image)
        color_frames = color_frames[-config.log.max_number_of_frames:] # hard limit the number of color_frames in ram
        
        depth_frames.append(runtime.depth_image)
        depth_frames = depth_frames[-config.log.max_number_of_frames:] # hard limit the number of color_frames in ram
        
        # 
        # check for saving to disk
        # 
        if len(color_frames) % save_to_disk_after == 0:
            save_frames_as_video(path=video_color_output_path)
        

def when_iteration_stops():
    save_frames_as_video(
        path=video_color_output_path,
    )

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
def save_frames_as_video(path):
    try:
        # save all the color_frames as a video

        # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # out = cv2.VideoWriter(path, fourcc, 20.0, (color_frames[0].shape[1], color_frames[0].shape[0]))

        # for frame in color_frames:
        #     out.write(frame)

        Video.create_from_frames(color_frames, save_to=path)
        print(f"\n\nvideo output has been saved to {path}")
        
        if video_depth_output_path:
            large_pickle_save(variable=depth_frames, file_path=video_depth_output_path)
    except Exception as error:
        pass

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
    color_image        = runtime.color_image
    found_robot        = runtime.modeling.found_robot
    current_confidence = runtime.modeling.current_confidence
    best_bounding_box  = runtime.modeling.best_bounding_box
    bounding_boxes     = runtime.modeling.bounding_boxes
    enemy_boxes        = runtime.modeling.enemy_boxes
    center_point       = runtime.aiming.center_point
    target_3d          = runtime.aiming.target_3d
    status             = runtime.aiming.target_status
    
    image = Image(runtime.color_image)

    if len(bounding_boxes) > 0:
        white  = rgb(255, 255, 255)
        red    = rgb(240, 113, 120)
        blue   = rgb(130, 170, 255)
        cyan   = rgb(137, 221, 255)
        green  = rgb(195, 232, 141)
        yellow = rgb(254, 195,  85)
        for each in bounding_boxes:
            # print(f"visual bounding_box: {each}")
            image.add_bounding_box(each, color=rgb(255, 255, 255))
        for each in enemy_boxes:
            image.add_bounding_box(each, color=rgb(254, 195,  85))
        if found_robot:
            image.add_bounding_box(best_bounding_box, color=rgb(240, 113, 120))
            image.add_point(x=center_point.x     , y=center_point.y     , color=rgb(130, 170, 255), radius=10)
            # image.add_point(x=prediction_point.x , y=prediction_point.y , color=rgb(195, 232, 141), radius=5)
    
    x_location = 30
    y_location = 50
    if (camera == "realsense"):
        image.add_text(text=f"target_3d: {    target_3d          :.2f}", location=(x_location, y_location)); y_location += 50
    image.add_text(text=f"confidence: {       current_confidence :.2f}", location=(x_location, y_location)); y_location += 50
    image.add_text(text=f"status: {           status.name            }", location=(x_location, y_location)); y_location += 50
    image.add_text(text=f"fps: {              fps                :.2f}", location=(x_location, y_location)); y_location += 50
        
    return image
