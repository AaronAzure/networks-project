import socket

# port number
port_num = 12345
socket_num = 0


def main():
    local_ip = socket.gethostbyname("localhost")

    # A TCP based echo server
    echo_socket = socket.socket()
 
    # Bind the IP address and the port number
    echo_socket.bind((str(local_ip), port_num))

    print("IP address = " + str(local_ip))
    print("listening on port=" + str(port_num) + ", sd=" + str(socket_num) + "\n")

    # Listen for incoming connections
    echo_socket.listen()

    # Start accepting client connections
    while(True):
        (clientSocket, clientAddress) = echo_socket.accept()

        # Handle one request from client
        while(True):
            data = clientSocket.recv(1024)
            print("At Server: %s"%data)

            if(data!=b''):
                # Send back what you received
                clientSocket.send(data)
                break

    

main()
