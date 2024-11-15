import socket
import threading
import subsystems.video_stream as video_stream
from toolbox.globals import config, print, runtime, time_synchronized



# Function to handle client communication
def handle_client(client_socket, client_address):
    print(f"New connection from {client_address}")

    # Send a welcome message to the client
    client_socket.send(b"Welcome to the server!\n")

    try:
        # Keep receiving data from the client
        while True:
            # Receive data from the client
            data = client_socket.recv(1024)
            if not data:
                # No data means the client has closed the connection
                break
            print(f"Received from {client_address}: {data.decode('utf-8')}")
            # Send a response back to the client
            response = f"Server received: {data.decode('utf-8')}\n"
            client_socket.send(response.encode('utf-8'))
            for runtime.frame_number, runtime.color_image, runtime.depth_image in video_stream.frames():
                client_socket.send(str(runtime.frame_number).encode('utf-8'))
    except Exception as e:
        print(f"Error with connection from {client_address}: {e}")
    finally:
        # Close the connection
        print(f"Closing connection with {client_address}")
        client_socket.close()


# Function to start the server
def start_server(host='127.0.0.1', port=65432):
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


# Entry point for the script
if __name__ == "__main__":
    start_server()
