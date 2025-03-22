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
import matplotlib.pyplot as plt
import time

pyston_lite.enable()
synchronized_debug = False
atexit.register(log.when_iteration_stops) # e.g. ctrl+C will trigger "when_iteration_stops" (its not perfectly reliable, but better than nothing)


fig , ax = plt.subplots()
plt.ion()
runtime.start_time = time.time()

x_data = []
x_error_data = []
y_error_data = []
z_error_data = []

line_x = ax.plot(0,0, label="x error", color="red",lw=2)[0]
line_y = ax.plot(0,0, label="y error" , color="green", lw=2)[0]
line_z = ax.plot(0,0, label="z error" , color="blue", lw=2)[0]

ax.set_xlabel("Time (s)")
ax.set_ylabel("Error")
ax.legend()
ax.grid(True)


# Run detection infinitely
for runtime.frame_number, runtime.color_image , runtime.depth_image in video_stream.frames():
    if synchronized_debug: t1 = time_synchronized()
    model.when_frame_arrives()
    
    if synchronized_debug: t2 = time_synchronized()
    aim.when_bounding_boxes_refresh()
    
    if synchronized_debug: t3 = time_synchronized()
    communicate.when_aiming_refreshes()
    
    
    new_time, error_x, error_y, error_z = log.plot_calculation()
    if new_time and error_x and error_y and error_z:
        # width = max(new_x+10)
        # height = max(new_y+10)
        # plt.figure(figsize=(width,height))
        x_data.append(new_time[0])
        x_error_data.append(error_x[0])
        y_error_data.append(error_y[0])
        z_error_data.append(error_z[0])

        line_x.set_data(x_data, x_error_data)
        line_y.set_data(x_data, y_error_data)
        line_z.set_data(x_data, z_error_data)


        ax.relim()
        ax.autoscale_view()

        plt.draw()
        #plt.pause(0.1)  # Prevent's freezing
    
   
    
    if synchronized_debug: t4 = time_synchronized()
    log.when_finished_processing_frame()
    
    
    
    log.plot_calculation()
    
    if synchronized_debug: t5 = time_synchronized()
    if synchronized_debug: print(f'\nframe {runtime.frame_number} took {1000*(t5-t1):.3f}ms' 
                                'model: {1000*(t2-t1):.3f}ms,' 
                                 'aim: {1000*(t3-t2):.3f}ms,'
                                 'communicate: {1000*(t4-t3):.3f}ms,' 
                                 'log: {1000*(t5-t4):.3f}ms')
    
    if synchronized_debug: print(f'average fps: {average_fps:.2f}')

if synchronized_debug: print(runtime.frame_number)
log.when_iteration_stops()

# plt.show()

