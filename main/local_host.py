import socket
import threading

import numpy

import subsystems.video_stream as video_stream
from toolbox.globals import config, print, runtime, time_synchronized
import pickle

currentFrameNum = 0
currentColorImage = 0
queue = numpy.empty((1,1))
# Function to handle client communication
def handle_client(client_socket, client_address):
    print(f"New connection from {client_address}")

    try:
        # Keep receiving data from the client
        serialized_data = pickle.dumps(queue)

        #data_size = len(serialized_data)
        #client_socket.sendall(data_size.to_bytes(10, byteorder='big'))  # Send size in 4 bytes

        client_socket.sendall(serialized_data)
    except Exception as e:
        print(f"Error with connection from {client_address}: {e}")
        client_socket.close()
    finally:
        # Close the connection
        print(f"Closing connection with {client_address}")
        client_socket.close()


# Function to start the server
def start_server(host='127.0.0.1', port=65433):
    # Create a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)  # Maximum number of clients the server can handle at once

    print(f"Server started on {host}:{port}. Waiting for connections...")

    # Accept incoming connections and handle each one in a new thread
    while True:
        client_socket, client_address = server_socket.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_handler.start()

def get_frame():
    for runtime.frame_number, runtime.color_image, runtime.depth_image in video_stream.frames():
        currentFrameNum = runtime.frame_number
        currentColorImage = runtime.color_image
        queue = currentColorImage


# Entry point for the script
if __name__ == "__main__":
    frames = threading.Thread(target=get_frame, args=())
    server = threading.Thread(target=start_server, args=())

    frames.start()
    server.start()
