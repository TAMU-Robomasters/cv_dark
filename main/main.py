import atexit
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import threading

from toolbox.globals import config, print, runtime, time_synchronized
from toolbox.autoboot_check import throw_if_autoboot_is_already_running
if config.mode != "production": throw_if_autoboot_is_already_running()

import subsystems.video_stream as video_stream
import subsystems.model        as model
import subsystems.aim          as aim
import subsystems.communicate  as communicate
import subsystems.power_rune   as power_rune 
import subsystems.log          as log
import pyston_lite

pyston_lite.enable()
synchronized_debug = False
atexit.register(log.when_iteration_stops) # e.g. ctrl+C will trigger "when_iteration_stops" (its not perfectly reliable, but better than nothing)

def shit():
    model.when_frame_arrives()
    aim.when_bounding_boxes_refresh()
    communicate.when_aiming_refreshes()
    log.when_finished_processing_frame()

# Run detection infinitely
for runtime.frame_number, runtime.color_image , runtime.depth_image in video_stream.frames():
    model_ps = threading.Thread(target=shit, args=())
    model_ps1 = threading.Thread(target=shit, args=())

    model_ps.start()
    model_ps1.start()

    if synchronized_debug: print(f'average fps: {average_fps:.2f}')



if synchronized_debug: print(runtime.frame_number)
log.when_iteration_stops()
