from ctypes import Structure, c_uint8, c_float, c_bool
import serial
import numpy as np
from time import time

from super_map import LazyDict

from toolbox.globals import path_to, config, print, runtime
from subsystems.aim import kf_3d
from subsystems.video_stream import video_stream


# 
# config
# 
serial_port  = config.communication.serial_port
baudrate     = config.communication.serial_baudrate

def setup_serial_port():
    print('') # spacer
    if not serial_port:
        print('[Communication]: Port=None so no communication')
        return None # disable port
    else:
        print(f'[Communication]: Port={serial_port}')
        try:
            return serial.Serial(
                serial_port,
                baudrate=baudrate,
                timeout=config.communication.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
        except Exception as error:
            import subprocess
            # very bad hack but it works
            subprocess.run([ "bash", "-c", f"sudo -S chmod 777 '{serial_port}' <<<  \"$(cat \"$HOME/.pass\")\" ",])
            return setup_serial_port() # recursion until it works


# 
# initialize
# 
port = setup_serial_port()

# C++ struct
# ? do we still need the magic number
class MessageToEmbedded(Structure):
    _pack_ = 1
    _fields_ = [
        ("magic_number"    , c_uint8   ),
        ("X"               , c_float   ),
        ("Y"               , c_float   ),
        ("Z"               , c_float   ),
        ("VX"               , c_float   ),
        ("VY"               , c_float   ),
        ("VZ"               , c_float   ),
        ("AX"               , c_float   ),
        ("AY"               , c_float   ),
        ("AZ"               , c_float   ),
        ("capture_delay"   , c_uint8   ),
        ("status"          , c_uint8   ),
    ]

message_to_embedded = MessageToEmbedded(ord('a'), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)

# 
# main
# 
def when_aiming_refreshes():
    global port
    capture_time =  getattr(video_stream, 'capture_time', 0)
    capture_delay = min(int(time()*1000 - capture_time), 255) # max 255 ms delay

    # Sending XYZ position (meters), velocity, acceleration, time since frame capture, and status of target relative to front of camera plane
    if runtime.aiming.target_3d is None:
        message_to_embedded.X = message_to_embedded.Y = message_to_embedded.Z = message_to_embedded.VX = message_to_embedded.VY = message_to_embedded.VZ = message_to_embedded.AX = message_to_embedded.AY = message_to_embedded.AZ = 0.0
    else:
        
        # estimating where the target is currently at
        #! not sure if this works
        target_kinematic_state = kf_3d.forward_predict(capture_delay)
        message_to_embedded.X = target_kinematic_state[0]
        message_to_embedded.Y = target_kinematic_state[1]
        message_to_embedded.Z = target_kinematic_state[2]
        message_to_embedded.VX = target_kinematic_state[3] 
        message_to_embedded.VX = target_kinematic_state[4]
        message_to_embedded.VZ = target_kinematic_state[5]
        message_to_embedded.AX = target_kinematic_state[6]
        message_to_embedded.AY = target_kinematic_state[7]
        message_to_embedded.AZ = target_kinematic_state[8]

    # TODO change capture delay to something more useful
    message_to_embedded.capture_delay = capture_delay
    message_to_embedded.status = runtime.aiming.target_status.value 
    print(f'''msg({f"X:{message_to_embedded.X:.4f}".rjust(7)}, {f"Y:{message_to_embedded.Y:.4f}".rjust(7)}, {f"Z:{message_to_embedded.Z:.4f}".rjust(7)},
        {f"VX:{message_to_embedded.X:.4f}".rjust(7)}, {f"VY:{message_to_embedded.Y:.4f}".rjust(7)}, {f"VZ:{message_to_embedded.Z:.4f}".rjust(7)},
        {f"AX:{message_to_embedded.X:.4f}".rjust(7)}, {f"AY:{message_to_embedded.Y:.4f}".rjust(7)}, {f"AZ:{message_to_embedded.Z:.4f}".rjust(7)},
        {f"delay:{message_to_embedded.capture_delay}"}ms, {f"status: {runtime.aiming.target_status.name}"})''', end=", ")
    
    try:
        port.write(bytes(message_to_embedded))
    except Exception as error:
        print(f"\n[Communication]: error when writing over UART: {error}")
        port = setup_serial_port() # attempt re-setup

# overwrite function if port is None
if port is None:
    def when_aiming_refreshes():
        pass # do nothing intentionally
