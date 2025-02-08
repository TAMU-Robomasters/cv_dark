"""
This is the main file for cv's auto-aim system.
"""
import atexit
import sys
import os
import pyston_lite

# run commmand: python3 main/main.py @CAMERA=REALSENSE @GUI
# run command with embedded: python3 main/main.py @CAMERA=REALSENSE @GUI @BOARD=XAVIER 

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from toolbox.globals import config, runtime, time_synchronized, print
from toolbox.autoboot_check import throw_if_autoboot_is_already_running
from subsystems import video_stream, model, aim, communicate, log, color_paper_detector

if config.mode != "production":
    throw_if_autoboot_is_already_running()

pyston_lite.enable()
SYNCHRONIZED_DEBUG = False

atexit.register(log.when_iteration_stops)
# i.e. ctrl+C will trigger "when_iteration_stops"
# (its not perfectly reliable, but better than nothing)

# Run detection infinitely
for runtime.frame_number, runtime.color_image , runtime.depth_image in video_stream.frames():
    if SYNCHRONIZED_DEBUG:
        t1 = time_synchronized()
    #model.when_frame_arrives() # TODO: change this to a function that detects a color piece of paper
    # return bounding box of the color piece of paper
    if SYNCHRONIZED_DEBUG:
        t2 = time_synchronized()
    color_paper_detector.paper_detector()

    if SYNCHRONIZED_DEBUG:
        t3 = time_synchronized()
    communicate.when_aiming_refreshes()

    if SYNCHRONIZED_DEBUG:
        t4 = time_synchronized()
    log.when_finished_processing_frame()

    if SYNCHRONIZED_DEBUG:
        t5 = time_synchronized()

        print(f'\nframe {runtime.frame_number} took {1000*(t5-t1):.3f}ms'
                                'model: {1000*(t2-t1):.3f}ms,' 
                                 'aim: {1000*(t3-t2):.3f}ms,'
                                 'communicate: {1000*(t4-t3):.3f}ms,' 
                                 'log: {1000*(t5-t4):.3f}ms') 
        print(f'average fps: {runtime.total_fps / runtime.get("frame_number", 1):.2f}')

if SYNCHRONIZED_DEBUG:
    print(runtime.frame_number)
log.when_iteration_stops()
