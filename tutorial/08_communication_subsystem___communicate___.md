# Chapter 8: Communication Subsystem (`communicate`)

In the [previous chapter](07_aiming_subsystem___aim___.md), we saw how the [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md) cleverly figures out the precise X, Y, and Z coordinates of the best enemy target in the real world. Our robot's "brain" now knows exactly where to point!

But how does this information get from the computer's calculations to the actual physical hardware – the motors that move the robot's turret or weapon? The brain needs a way to talk to the muscles.

## The Problem: Bridging the Digital and Physical Worlds

Imagine you're controlling a robot arm using your computer. You calculate that the arm needs to move to coordinates (10, 20, 30). How do you send that command to the actual motors controlling the arm? You can't just shout it!

Our auto-aim system faces the same challenge. The aiming calculations happen in the software (Python code running on a computer, maybe the robot's onboard computer). The physical aiming mechanism (like a turret) is usually controlled by a separate, simpler piece of hardware called a **microcontroller** (think of a small, dedicated computer like an Arduino or Teensy).

We need a reliable way to send the calculated aiming coordinates (X, Y, Z) from our main Python program to this microcontroller.

## The Solution: `communicate` - The System's Voice

The **Communication Subsystem (`communicate`)** acts as the voice of our auto-aim system. Its job is to take the final instructions from the brain (`aim`) and deliver them clearly to the body (the microcontroller controlling the turret).

Here's how it works:

1.  **Gets the Aiming Data:** It reads the final `target_3d` coordinates (X, Y, Z) and the `target_status` (did we find a target?) from the [Shared Runtime Data (`runtime`)](03_shared_runtime_data___runtime___.md) blackboard.
2.  **Formats the Message:** The microcontroller expects data in a very specific, predictable format. The `communicate` subsystem packages the X, Y, Z coordinates, status, and maybe some timing information (like how long ago the image was captured) into this exact structure. Think of it like filling out a form the microcontroller knows how to read. In our project, this structure is defined like a C/C++ `struct`.
3.  **Sends the Message:** It sends this structured data package over a **serial port** (also known as UART). Imagine a simple USB cable connecting the main computer to the microcontroller; the serial port sends data electrically through this cable, one bit after another.

This subsystem ensures that the physical hardware gets the correct aiming instructions based on what the vision system sees and the aiming system decides.

## How the Main Loop Uses `communicate`

The `communicate` subsystem is called near the end of the [Main Execution Loop](01_main_execution_loop_.md), right after the `aim` subsystem has finished its calculations.

```python
# File: main.py (Simplified loop)

from subsystems import video_stream, model, aim, communicate # Import subsystems
from toolbox.globals import runtime # Import shared data

# Get frame, analyze, calculate aim...
for runtime.frame_number, runtime.color_image, runtime.depth_image in video_stream.frames():

    # 1. Model finds targets
    model.when_frame_arrives()

    # 2. Aim calculates the 3D aim point
    aim.when_bounding_boxes_refresh()
    # Aiming results (target_3d, target_status) are now in runtime.aiming

    # ---> 3. Communicate sends the command to hardware <---
    communicate.when_aiming_refreshes()

    # 4. Log what happened
    # log.when_finished_processing_frame()
```

The key call is `communicate.when_aiming_refreshes()`. This function, located in `subsystems/communicate.py`, does the actual work of packaging and sending the data.

Let's look inside a simplified version of `communicate.when_aiming_refreshes()`:

```python
# File: subsystems/communicate.py (Simplified 'when_aiming_refreshes')

from toolbox.globals import runtime, config, print # Use runtime, config
from ctypes import Structure, c_uint8, c_float # For the C-style struct
import serial # For serial communication
from time import time
from subsystems.video_stream import video_stream # To get capture time

# Define the structure the microcontroller expects
class MessageToEmbedded(Structure):
    _pack_ = 1 # Important for ensuring data aligns correctly
    _fields_ = [
        ("magic_number", c_uint8), # A check byte
        ("X"           , c_float), # Aiming X coord (meters)
        ("Y"           , c_float), # Aiming Y coord (meters)
        ("Z"           , c_float), # Aiming Z coord (meters)
        ("capture_delay", c_uint8), # Time since image capture (ms)
        ("status"      , c_uint8), # Target status code
    ]

# Create an instance of the structure to fill
message_to_embedded = MessageToEmbedded(ord('a'), 0.0, 0.0, 0.0, 0, 0)

# Assume 'port' is the opened serial connection (setup elsewhere)
# port = serial.Serial(...) # This happens when the program starts

def when_aiming_refreshes():
    # 1. Read data from runtime
    target_3d = runtime.aiming.target_3d
    target_status = runtime.aiming.target_status.value # Get the numeric value
    capture_time = getattr(video_stream, 'capture_time', 0) # Get time frame was taken
    capture_delay = min(int(time()*1000 - capture_time), 255) # Delay in ms (max 255)

    # 2. Fill the message structure
    if target_3d is None:
        # No target found, send zeros
        message_to_embedded.X = 0.0
        message_to_embedded.Y = 0.0
        message_to_embedded.Z = 0.0
    else:
        # Target found, send its coordinates
        message_to_embedded.X = float(target_3d[0])
        message_to_embedded.Y = float(target_3d[1])
        message_to_embedded.Z = float(target_3d[2])
    
    message_to_embedded.capture_delay = capture_delay
    message_to_embedded.status = target_status

    # 3. Send the data over the serial port
    try:
        # 'bytes()' converts the structure into raw bytes
        port.write(bytes(message_to_embedded))
        print(f"Sent: X={message_to_embedded.X:.2f}, ...", end="") # Show what was sent
    except Exception as e:
        print(f"\n[Communication Error]: {e}")
        # Try to reopen the port if sending failed (simplified)
        # port = setup_serial_port()
```

Let's break it down:
1.  **Read Data:** It grabs the `target_3d` point, the `target_status`, and calculates the `capture_delay` (how old the frame was when this command is sent) from the `runtime` blackboard and the [Video Stream Subsystem](04_video_stream_subsystem_.md).
2.  **Fill Structure:** It populates the fields of the `message_to_embedded` object. If `target_3d` is `None` (meaning `aim` didn't find a valid target), it sends coordinates (0, 0, 0). Otherwise, it sends the calculated X, Y, Z values. It also adds the delay and status code.
3.  **Send Data:** The `port.write(bytes(message_to_embedded))` line is where the magic happens. `bytes()` turns our Python structure into a sequence of raw bytes exactly matching the C/C++ struct definition. `port.write()` then sends these bytes out through the serial connection to the waiting microcontroller. It's wrapped in a `try...except` block to catch errors if the serial connection fails.

Notice that the specific serial port (`/dev/ttyACM0`, `COM3`, etc.) and the communication speed (`baudrate`) are configured in the `info.yaml` file and accessed via the [Global Configuration (`config`)](02_global_configuration___config___.md).

## Under the Hood: Setting Up and Sending

How does the system establish this communication channel?

**1. Opening the Serial Port (`setup_serial_port`)**

When the `communicate.py` file is first loaded (near program start), it runs a function to set up the serial connection:

```python
# File: subsystems/communicate.py (Simplified setup)
import serial
from toolbox.globals import config, print

def setup_serial_port():
    # Get settings from the config file
    port_name = config.communication.serial_port
    baud_rate = config.communication.serial_baudrate
    timeout = config.communication.timeout

    if not port_name:
        print("[Communication]: Serial port not specified in config. Disabled.")
        return None # No communication possible

    print(f"[Communication]: Trying to open {port_name} at {baud_rate} baud.")
    try:
        # Use the 'pyserial' library to open the connection
        connection = serial.Serial(
            port_name,
            baudrate=baud_rate,
            timeout=timeout,
            # Other settings usually stay default
        )
        print("[Communication]: Serial port opened successfully.")
        return connection
    except Exception as e:
        print(f"[Communication Error]: Could not open port {port_name} - {e}")
        print("Check permissions (e.g., 'sudo chmod 777 ...') or if port is correct.")
        # (The actual code might try a permission fix automatically)
        return None

# Call the setup function and store the result globally in this file
port = setup_serial_port()

# If setup failed, redefine the main function to do nothing
if port is None:
    def when_aiming_refreshes():
        pass # Communication disabled
```

This setup code:
*   Reads the port name, speed (baud rate), and timeout value from `config`.
*   Uses the `serial.Serial()` function (from the `pyserial` library) to try and open the connection.
*   Handles errors if the port can't be opened (e.g., wrong name, device not plugged in, permissions issue).
*   Stores the resulting connection object in the `port` variable for `when_aiming_refreshes` to use. If it fails, `port` remains `None`, and a dummy `when_aiming_refreshes` function is used to prevent errors later.

**2. The Data Structure (`MessageToEmbedded`)**

Why use `ctypes.Structure`? Microcontrollers (often programmed in C or C++) work directly with fixed memory layouts. Using `ctypes.Structure` with `_pack_=1` ensures that our Python data (X, Y, Z floats, status uint8, etc.) is arranged in memory *exactly* the way the C code on the microcontroller expects to receive it. Any mismatch in size or order would lead to garbled data. The `magic_number` (like `ord('a')`) acts as a simple check; the microcontroller can look for this byte at the start to verify it's receiving a valid message packet.

**3. The Sending Process (`port.write`)**

The `port.write(bytes(...))` command takes the byte representation of our `MessageToEmbedded` structure and pushes it out bit-by-bit over the serial wire according to the agreed speed (baud rate). The microcontroller on the other end listens for incoming bytes on its serial input pin, reassembles them according to the *same* structure definition (defined in its C/C++ code), and then uses the X, Y, Z values to command its motors.

**Simplified Sequence Diagram**

```mermaid
sequenceDiagram
    participant Loop as Main Loop
    participant Comm as Communicate Subsystem
    participant RT as runtime Blackboard
    participant Serial as Serial Port Hardware
    participant MicroC as Microcontroller

    Loop->>Comm: Call when_aiming_refreshes()
    Comm->>RT: Read aiming.target_3d, status, etc.
    Comm->>Comm: Format data into MessageToEmbedded struct
    Comm->>Serial: port.write(bytes(message))
    Serial-->>MicroC: Transmits electrical signals (bytes)
    MicroC->>MicroC: Receives bytes, parses struct
    MicroC->>MicroC: Uses X, Y, Z to control motors
    Comm-->>Loop: Done sending for this frame
```

## Conclusion

The **Communication Subsystem (`communicate`)** is the final link in the chain, acting as the system's voice to the physical world. It takes the computed 3D aiming coordinates from the [Aiming Subsystem (`aim`)](07_aiming_subsystem___aim___.md) (via the [Shared Runtime Data (`runtime`)](03_shared_runtime_data___runtime___.md)), carefully packages them into a structured format defined using `ctypes`, and transmits this package over a serial (UART) connection configured by the [Global Configuration (`config`)](02_global_configuration___config___.md). This ensures the robot's hardware receives the precise instructions needed to point its turret or weapon at the intended target, effectively translating digital calculations into physical action.

We've now followed the journey from capturing an image to sending a command to the hardware. But how do we keep track of everything that happened along the way? How fast is the system running? Did it find targets? What commands were sent? That's where our final subsystem comes in.

Next: [Chapter 9: Logging Subsystem (`log`)](09_logging_subsystem___log___.md)

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)