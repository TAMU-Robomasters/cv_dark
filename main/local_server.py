import socket
import threading

def handle_client(client_socket, client_address):
    """Handles communication with a single client."""
    while True:

        data = client_socket.recv(1024)
        if not data:
            break
        print(f"Received from {client_address}: {data.decode()}")
        client_socket.send(b"Message received")

    client_socket.close()

def start_server():
    """Starts the server and listens for incoming connections."""
    host = 'localhost'
    port = 5000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)

    print(f"Server listening on {host}:{port}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Accepted connection from {client_address}")
        thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        thread.start()

if __name__ == "__main__":
    start_server()