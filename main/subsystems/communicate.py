import requests
import json
import time
import serial
import os
import sys
import atexit
import numpy as np
import struct
from super_map import LazyDict
from ctypes import Structure, c_uint8, c_float, c_bool

# Local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from toolbox.globals import path_to, config, print, runtime
from subsystems.aim import kf_3d
from subsystems.video_stream import video_stream
from subsystems.aim import TargetStatus


# Config
serial_port = config.communication.serial_port
baudrate = config.communication.serial_baudrate
SERVER_URL = "http://localhost:8000"

# Command codes for communication protocol
ROBO_DATA = (b'r')       # Command code for robot data
ODO = (b'o')             # Command code for odometry  
TRANSFORM = (b't')       # Command code for transform

# Message Structures
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

class OdometryDataFromEmbedded(Structure):
    _pack = 1
    _fields_ = [
        ("x_field", c_float),
        ("y_field", c_float),
        ("yaw_angle", c_float)
    ]

TRANSFORMATION_FORMAT = 'f' * 16

# For Debugging
rxBuffer = []
def print_buffer():
	print(rxBuffer)
	print(port.in_waiting)

atexit.register(print_buffer)


# Serial port setup and initialization
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
            print(f"[Communication]: Error setting up serial port: {error}")
            import subprocess
            # very bad hack but it works
            # FIXME
            subprocess.run([ "bash", "-c", f"sudo -S chmod 777 '{serial_port}' <<<  \"$(cat \"$HOME/.pass\")\" ",])
            return setup_serial_port() # recursion until it works

port = setup_serial_port()
message_to_embedded = MessageToEmbedded(ord('a'), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 0)
# odo_data = OdometryDataFromEmbedded(0.0,0.0,0.0)


# Server communication function
def send_object(object):
    # Send a python object to server
    data = json.dumps({"object": object})

    start_time = time.time()
    response = requests.post(SERVER_URL, data=data)
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Server response: {response.text} (Processed in {elapsed_time:.4f} seconds)")

def get_number():
    "# Request stored number from server"
    start_time = time.time()
    response = requests.get(SERVER_URL)
    end_time = time.time()
    elapsed_time = end_time - start_time
    if response.status_code == 200:
        data = response.json()
        print(f"Stored number: {data['number']} (Processed in {elapsed_time:.4f} seconds)")
    else:
        print("Error retrieving number.")


# Main communication functions
def when_aiming_refreshes():
    global port
    capture_time =  getattr(video_stream, 'capture_time', 0)
    capture_delay = min(int(time.time()*1000 - capture_time), 255) # max 255 ms delay

    # Sending XYZ position (meters), velocity, acceleration, time since frame capture, and status of target relative to front of camera plane
    if runtime.target_status == TargetStatus.TARGET_NONE:
        message_to_embedded.X = message_to_embedded.Y = message_to_embedded.Z = message_to_embedded.VX = message_to_embedded.VY = message_to_embedded.VZ = message_to_embedded.AX = message_to_embedded.AY = message_to_embedded.AZ = 0.0
    else:
        
        # estimating where the target is currently at
        #! not sure if this works
        print(f"dt communicate.py: {capture_delay / 1E3}")
        target_kinematic_state = kf_3d.forward_predict(capture_delay / 1E3) # KF works with seconds for time
        print(f"pos communicate.py {target_kinematic_state[0]}, {target_kinematic_state[3]}, {target_kinematic_state[6]}")
        message_to_embedded.X = target_kinematic_state[0]
        message_to_embedded.Y = target_kinematic_state[3]
        message_to_embedded.Z = target_kinematic_state[6]
        message_to_embedded.VX = target_kinematic_state[1] 
        message_to_embedded.VY = target_kinematic_state[4]
        message_to_embedded.VZ = target_kinematic_state[7]
        message_to_embedded.AX = target_kinematic_state[2]
        message_to_embedded.AY = target_kinematic_state[5]
        message_to_embedded.AZ = target_kinematic_state[8]

    # TODO change capture delay to something more useful
    message_to_embedded.capture_delay = capture_delay
    message_to_embedded.status = runtime.aiming.target_status.value 
    print(f'''msg({f"X:{message_to_embedded.X:.4f}".rjust(7)}, {f"Y:{message_to_embedded.Y:.4f}".rjust(7)}, {f"Z:{message_to_embedded.Z:.4f}".rjust(7)},
        {f"VX:{message_to_embedded.VX:.4f}".rjust(7)}, {f"VY:{message_to_embedded.VY:.4f}".rjust(7)}, {f"VZ:{message_to_embedded.VZ:.4f}".rjust(7)},
        {f"AX:{message_to_embedded.AX:.4f}".rjust(7)}, {f"AY:{message_to_embedded.AY:.4f}".rjust(7)}, {f"AZ:{message_to_embedded.AZ:.4f}".rjust(7)},
        {f"delay:{message_to_embedded.capture_delay}"}ms, {f"status: {runtime.aiming.target_status.name}"})''', end=", ")
    
    try:
        port.write(bytes(message_to_embedded))
    except Exception as error:
        print(f"\n[Communication]: error when writing over UART: {error}")
        port = setup_serial_port() # attempt re-setup

def communicate_read(message_dict):
    global port
    try:
        byte = port.read(1)
        if byte == b'b':  # Sync/start byte
            byte = port.read(1)
            if not byte:
                return

            command = byte

            if command == ROBO_DATA:
                data_byte = port.read(1)
                if not data_byte:
                    return
                data = data_byte[0]
                team_color = data & 0b0001              # bit 0
                robot_ID = (data & 0b1110) >> 1         # bits 1-3
                # TODO: change model.py based on team_color
                return

            elif command == ODO:
                data_bytes = port.read(12)
                if len(data_bytes) != 12:
                    return
                odo_data = OdometryDataFromEmbedded.from_buffer_copy(data_bytes)
                rxBuffer.append(odo_data)
                return

            elif command == TRANSFORM:
                # TODO: Handle TRANSFORM logic
                float_bytes = port.read(64)
                print(f"In reading buffer: {port.in_waiting}")
                float_tuple = struct.unpack(TRANSFORMATION_FORMAT, float_bytes)
                
                if len(float_tuple) != 16:
                    return False
                
                timestamp = time.time()
                message_dict["Message"] = {"Timestamp": timestamp, "Float Tuple": float_tuple}
                
                return True 
            else:
                # Unknown command
                return

        else:
            return

    except Exception as error:
        print(f"\n[Communication]: error when read over UART: {error}")
        port = setup_serial_port()  # Reinitialize the port

def test_communicate_read():
    global port
    try:
        byte = port.read(1)
        if(byte):
            rxBuffer.append(byte)
            number = byte.decode('ascii')

            send_object(number)

        else:
            print("no byte")
    except Exception as error:
        print(f"\n[Communication]: error when read over UART: {error}")
        port = setup_serial_port()  # attempt re-setup


# Handle case when port is not available
if port is None:
    def when_aiming_refreshes():
        pass # do nothing intentionally
    def test_communicate_read():
        pass

# Main execution
if __name__ == "__main__":
    while True:
        message_dict = {"Message": "None"}
        if communicate_read(message_dict):
            send_object(message_dict)
        
