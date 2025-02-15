import json
import cv2
from time import time as now
from datetime import datetime as dt

from toolbox.globals import path_to, config, print, runtime, absolute_path_to
from toolbox.video_tools import Video, VideoWriter
from toolbox.image_tools import Image, rgb
from toolbox.cold_storage import ColdStorage
from subsystems.aim import TargetStatus
from subsystems.video_stream import video_stream

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation 
import os
import numpy as np
import time



# 
# config
# 
display_live_frames         = config.log.display_live_frames
save_frame_to_file          = config.log.save_frame_to_file
display_kf_prediction       = config.log.display_kf_prediction
kf_fig_dir                  = absolute_path_to.kalman_filter_error_figs
save_depth                  = config.log.save_depth
save_rate                   = config.log.save_rate
record_video_output_color   = absolute_path_to.record_video_output_color
video_output                = absolute_path_to.video_output
camera                      = config.hardware.camera
depth_compatible            = config.hardware.camera_has_depth
should_benchmark            = config.mode == 'benchmark'
MIN_RANGE                   = config.aiming.min_range
MAX_RANGE                   = config.aiming.max_range



# create incremented storage path
time_stamp = dt.now().strftime("%m%d%y-%H:%M")
video_color_output_path = f'{absolute_path_to.record_video_output_color}-{time_stamp}.color.ignore.mp4'
video_depth_output_path = None
if depth_compatible and save_depth:
    video_depth_output_path = f'{absolute_path_to.record_video_output_color}-{time_stamp}.depth.ignore.mp4'

color_video_writer = VideoWriter(save_to=video_color_output_path, fps=config.log.estimated_framerate)
depth_video_writer = VideoWriter(save_to=video_depth_output_path, fps=config.log.estimated_framerate) if video_depth_output_path else None

center_points = []
center_point_predictions = [] 

target_3d_points = []
target_3d_predictions = []





# 
# 
# main
# 
# 
runtime.prev_loop_time = int(now() * 1000) # init time value
runtime.total_fps = 0


# Not sure if we are to continue using this
def init_log_plots():
    fig, ax = plt.subplots()
    # ax.set_xlim(0, 10)  # Initial x-range
    # ax.set_ylim(-10, 10)  # Initial y-range
    fig.tight_layout()
    line, = ax.plot([], [], lw=2)

    runtime.start_time = time.time()
    return fig, ax, line
    
def plot_calculation():
    center_point            = runtime.aiming.center_point
    center_point_prediction = runtime.aiming.center_point_prediction
    target_3d_point         = runtime.aiming.target_3d
    target_3d_prediction    = runtime.aiming.target_3d_prediction
    
    if target_3d_point is None or target_3d_prediction is None:
        return [], []

    error = np.linalg.norm(np.array(target_3d_prediction) - np.array(target_3d_point))

    
    elapsed_time = time.time() - runtime.start_time
    floaterr = float(error)
    print("prediction 0",target_3d_prediction[0])
    print("prediction 0",target_3d_prediction[1])
    print("prediction 0",target_3d_prediction[2])
    print("target 3d point 0", target_3d_point[0])
    print("target 3d point 1", target_3d_point[1])
    print("target 3d point 2", target_3d_point[2])
    print("point runtime", runtime.aiming.target_3d)
    print("prediction runtime", runtime.aiming.target_3d_prediction)
    
    x_data = [elapsed_time]
    y_data = [floaterr]
    print("FLOATERR",y_data)
    print("Time",x_data)
    return  x_data,y_data
    
    
    
    
    
    

def when_finished_processing_frame():
    global color_video_writer
    global depth_video_writer
    print("REACHED FRAME PROCESSING")
    
    # import data
    frame_number            = runtime.frame_number
    color_image             = runtime.color_image
    depth_image             = runtime.depth_image
    prev_loop_time          = runtime.prev_loop_time
    bounding_boxes          = runtime.modeling.bounding_boxes
    center_point            = runtime.aiming.center_point
    center_point_prediction = runtime.aiming.center_point_prediction
    target_3d_point         = runtime.aiming.target_3d
    target_3d_prediction    = runtime.aiming.target_3d_prediction
    
    center_points.append(center_point)
    center_point_predictions.append(center_point_prediction)
    
    target_3d_points.append(target_3d_point)
    target_3d_predictions.append(target_3d_prediction)
    
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
    
    if display_kf_prediction and depth_compatible and target_3d_point != None:
        #! hotfix [1] [2]
        print("target:", target_3d_point)
        print("target_prediction:", target_3d_prediction)
        depth = show_depth_prediction(target_3d_point[1], target_3d_prediction[2])


        
    if display_live_frames:
            # if depth_compatible:
                # cv2.imshow("depth", depth.img)
                # plt.show(block=False)
                # plt.close()
            cv2.imshow("main", image.img)
            cv2.waitKey(1) # doesn't actually wait  
    
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
    plt.ioff()
    plt.show()
    # Find average error
    
    # account for divide by zero error, no target center point none
    # More than 4 index (do top first)
    
    # predict error using the error estimation formula
    # predicted_errors_x = []
    # for i in range(0,(len(center_points)-1)):
    #     if(center_points[i+1].x != 0 and i >= 4):
    #         predicted_error = abs((center_point_predictions[i].x - center_points[i+1].x)/ center_points[i+1].x) * 100
    #         predicted_errors_x.append(predicted_error)
    
    # predicted_errors_y = []
    # for i in range(0,(len(center_points)-1)):
    #     if(center_points[i+1].y != 0 and i >= 4):
    #         predicted_error = abs((center_point_predictions[i].y - center_points[i+1].y)/ center_points[i+1].y) * 100
    #         predicted_errors_y.append(predicted_error)
    
    # if not depth_compatible and display_kf_prediction:
    #     # Convert to np array
    #     # predicted_errors_np_x = np.array(predicted_errors_x)
    #     # predicted_errors_np_y = np.array(predicted_errors_y)

    #     # # Plot functions for 2d
    #     # fig, (ax1, ax2) = plt.subplots(2, 1) 
    #     # index = np.arange(0, len(predicted_errors_np_x),1)

    #     # ax1.plot(index, predicted_errors_np_x)
    #     # ax1.set_title('Predicted error x')

    #     # ax2.plot(index, predicted_errors_np_y)
    #     # ax2.set_title('Predicted error y')

    #     plt.tight_layout()
        
    #     # git ignore will ignore files with *.ignore.*
    #     kf_fig_2d_path = f'{kf_fig_dir}/2d/-{time_stamp}.ignore.jpg'
    #     plt.savefig(kf_fig_2d_path)

    # if depth_compatible and display_kf_prediction:
    #     # 3d prediction error 
    #     predicted_errors_3d_x = []
    #     for i in range(0,(len(target_3d_points)-1)):
    #         if(target_3d_points[i+1][0] != 0 and i >= 4):
    #             predicted_error = abs((target_3d_predictions[i].x - target_3d_points[i+1][0])/ target_3d_points[i+1][0]) * 100
    #             predicted_errors_3d_x.append(predicted_error)
                
    #     predicted_errors_3d_y = []
    #     for i in range(0,(len(target_3d_points)-1)):
    #         if(target_3d_points[i+1][1] != 0 and i >= 4):
    #             predicted_error = abs((target_3d_predictions[i].y - target_3d_points[i+1][1])/ target_3d_points[i+1][1]) * 100
    #             predicted_errors_3d_y.append(predicted_error)
                
    #     predicted_errors_3d_z = []
    #     for i in range(0,(len(target_3d_points)-1)):
    #         if(target_3d_points[i+1][2] != 0 and i >= 4):
    #             predicted_error = abs((target_3d_predictions[i].z - target_3d_points[i+1][2])/ target_3d_points[i+1][2]) * 100
    #             predicted_errors_3d_z.append(predicted_error)
        
        
    #     predicted_errors_np_3d_x = np.array(predicted_errors_3d_x)
    #     predicted_errors_np_3d_y = np.array(predicted_errors_3d_y)
    #     predicted_errors_np_3d_z = np.array(predicted_errors_3d_z)
  
    #     # plot functions for 3d
    #     fig, (ax1, ax2,ax3) = plt.subplots(3, 1) 
    #     index = np.arange(0, len(predicted_errors_np_3d_x),1)
    #     print(predicted_errors_np_3d_x)

    #     ax1.plot(index, predicted_errors_np_3d_x)
    #     ax1.set_title('Predicted error x')

    #     ax2.plot(index, predicted_errors_np_3d_y)
    #     ax2.set_title('Predicted error y')
        
    #     ax3.plot(index, predicted_errors_np_3d_z)
    #     ax3.set_title('Predicted error z')

    #     plt.tight_layout()
        
    #     kf_fig_3d_path = f'{kf_fig_dir}/3d/-{time_stamp}.ignore.jpg'
    #     plt.savefig(kf_fig_3d_path)
        
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


def show_depth_prediction(depth, depth_prediction):
    """
    Display a window that shows Y value of the target and
    the predicted Y value of the target based of the Kalman Filter stuff
    """
    total_range = MAX_RANGE - MIN_RANGE

    # normalize the depth
    norm_depth = (depth - MIN_RANGE) / total_range
    norm_depth_prediction =  (depth_prediction - MIN_RANGE) / total_range

    depth = Image(np.zeros((848, 100, 3)))

    depth.add_point(x=50, y=norm_depth * 848, color=rgb(130, 170, 255), radius=10)
    depth.add_point(x=50, y=norm_depth_prediction * 848, color=rgb(195, 232, 141), radius=10)
    print("realsense depth:", norm_depth)
    print("kalman filter depth:", norm_depth_prediction)

    return depth


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

    # TODO possibly define these globally
    if len(bounding_boxes) > 0:
        white           = rgb(255, 255, 255)
        red             = rgb(255,   0,   0)
        blue            = rgb(130, 170, 255)
        cyan            = rgb(137, 221, 255)
        green           = rgb(195, 232, 141)
        yellow          = rgb(254, 195,  85)
        light_orange    = rgb(254, 195,  85)

        for each in bounding_boxes:
            image.add_bounding_box(each, color=white)
        for each in enemy_boxes:
            image.add_bounding_box(each, color=light_orange)
        if status == TargetStatus.TARGET_FOUND:
            image.add_bounding_box(best_bounding_box, color=red)
            image.add_point(x=center_point.x     , y=center_point.y     , color=blue, radius=10)
        if display_kf_prediction:
            if depth_compatible:
                target_3d_pixel = video_stream.point_3d_to_pixel(target_3d_prediction)
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
