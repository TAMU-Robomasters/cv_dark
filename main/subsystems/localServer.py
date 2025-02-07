import socket
import threading

# Define server host and port
HOST = 'localhost'  # Localhost
PORT = 65432        # Port to listen on

output_dict = {}


# Function to handle each client connection
def handle_client(conn, addr):
    #print(f"Connected by {addr}")
    with conn:
        while True:
            # Receive data from the client
            data = conn.recv(1024)
            data_str = data.decode("utf-8")
            if not data:
                break
            #print(f"Received from {addr}: {data.decode('utf-8')}")
            index = data_str.index(":")
            output_dict[data_str[:index]] = data_str[index+2:index + 13]
            print(output_dict)
    print(f"Connection with {addr} closed")

# Main server setup
def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        #print(f"Server is listening on {HOST}:{PORT}")

        while True:
            # Accept new client connections
            conn, addr = server_socket.accept()
            # Start a new thread to handle the client
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.start()

# Start the server
start_server()