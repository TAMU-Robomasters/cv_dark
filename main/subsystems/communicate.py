from ctypes import *
import serial
from time import time

from super_map import LazyDict

from toolbox.globals import path_to, config, print, runtime
from subsystems.communicating.serial_help import setup_serial_port
from subsystems.video_stream import video_stream

# 
# config
# 
serial_port  = config.communication.serial_port
baudrate     = config.communication.serial_baudrate

# 
# initialize
# 
port = setup_serial_port()

# C++ struct
class Message(Structure):
    _pack_ = 1
    _fields_ = [
        ("magic_number"    , c_uint8   ),
        ("X"               , c_float   ),
        ("Y"               , c_float   ),
        ("Z"               , c_float   ),
        ("capture_delay"   , c_uint8   ),
        ("status"          , c_uint8   ),
    ]
message = Message(ord('a'), 0.0, 0.0, 0.0, 0, 0)

# 
# main
# 
def when_aiming_refreshes():
    global port
    capture_time =  getattr(video_stream, 'capture_time', 0)
    capture_delay = min(int(time()*1000 - capture_time), 255) # max 255 ms delay

    # Sending XYZ position (meters), time since frame capture, and status of target relative to front of camera plane
    if runtime.aiming.target_3d is None:
        message.X = message.Y = message.Z = 0.0
    else:
        message.X = float(runtime.aiming.target_3d[0])
        message.Y = float(runtime.aiming.target_3d[1])
        message.Z = float(runtime.aiming.target_3d[2])
    message.capture_delay = capture_delay
    message.status = runtime.aiming.target_status.value
    print(f'''msg({f"X:{message.X:.4f}".rjust(7)}, {f"Y:{message.Y:.4f}".rjust(7)}, {f"Z:{message.Z:.4f}".rjust(7)}, {f"delay:{message.capture_delay}"}ms, {f"status: {runtime.aiming.target_status.name}"})''', end=", ")
    
    try:
        port.write(bytes(message))
    except Exception as error:
        print(f"\n[Communication]: error when writing over UART: {error}")
        port = setup_serial_port() # attempt re-setup

# overwrite function if port is None
if port is None:
    def when_aiming_refreshes():
        pass # do nothing intentionally

# 
# helpers
# 
def read_input():
    """
    Read data from DJI board
    :returns: received data (ended with EOL) as a string
    """
    if port is not None:
        return port.readline()
