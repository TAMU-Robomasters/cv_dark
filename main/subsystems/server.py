#todo add server codea
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# communicate.py reads over data from UART from embedded (the devboard)
# and then sends it to the server
# and then server sends it to aim

# then aim will do some math, send the server ummm what would it be, 9 numbers, and then the
# server will send those 9 numbers to communicate.py
# then communicate.py will send that to the devboard over UART

# the two clients will be communicate.py and aim.py (auto aim)



# Receive and decode byte (byte is in ascii)
from http.server import BaseHTTPRequestHandler, HTTPServer
import json


stored_object = None

class NumberHandler(BaseHTTPRequestHandler):
    # Handle a GET request to send the stored object
    def do_GET(self):
        global stored_object
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = {"object": stored_object}
        self.wfile.write(json.dumps(response).encode())

    # Handle POST request to receive an object and store it
    def do_POST(self):
        global stored_object
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        received_data = json.loads(post_data)

        if "object" in received_data:
            stored_object = received_data["object"]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(f'Object received: {stored_object}'.encode())
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid data format")

if __name__ == "__main__":
    server_address = ("", 8000)
    httpd = HTTPServer(server_address, NumberHandler)
    print("Server running in port 8000")
    httpd.serve_forever()
