import atexit
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from toolbox.globals import config, print, runtime, time_synchronized
import subsystems.video_stream as video_stream
import subsystems.model        as model
import subsystems.aim          as aim
import subsystems.communicate  as communicate
import subsystems.power_rune   as power_rune 
import subsystems.log          as log
import pyston_lite

import subsystems.aim as aim
import subsystems.aruco_detection as aruco_detection
import subsystems.communicate as communicate
# import subsystems.power_rune as power_rune
import subsystems.log as log
import subsystems.model as model
import subsystems.video_stream as video_stream
from toolbox.globals import print, runtime, time_synchronized

pyston_lite.enable()
synchronized_debug = False
atexit.register(
    log.when_iteration_stops)  # e.g. ctrl+C will trigger "when_iteration_stops" (its not perfectly reliable, but better than nothing)

# Run detection infinitely
for runtime.frame_number, runtime.color_image, runtime.depth_image in video_stream.frames():
    if synchronized_debug: t1 = time_synchronized()
    model.when_frame_arrives()

    if synchronized_debug: t2 = time_synchronized()
    aim.when_bounding_boxes_refresh()

    if synchronized_debug: t3 = time_synchronized()
    aruco_detection.when_detection_refreshes()

    if synchronized_debug: t4 = time_synchronized()

    # TODO: Do you want to add another timestamp between these communication events?
    communicate.when_aiming_refreshes()
    communicate.when_aruco_refreshes()

    if synchronized_debug: t5 = time_synchronized()
    log.when_finished_processing_frame()

    if synchronized_debug: t6 = time_synchronized()
    if synchronized_debug: print(
        f'\nframe {runtime.frame_number} took {t6 - t1:.3f} seconds. model: {t2 - t1:.3f}, aim: {t3 - t2:.3f}, aruco_detection: {t4 - t3:.3f}, communicate: {t5 - t4}, log: {t6 - t5:.3f}')
    if synchronized_debug: print(f'average fps: {average_fps:.2f}')

if synchronized_debug: print(runtime.frame_number)
log.when_iteration_stops()
