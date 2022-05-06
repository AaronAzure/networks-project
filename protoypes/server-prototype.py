import os
import sys
import socket

port_num = 12345
socket_num = 0


def main():
    # A TCP based echo server
    echo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
    # Bind the IP address and the port number
    echo_socket.bind(('localhost', port_num))

    # print("IP address = " + str(local_ip))
    print("listening on port=" + str(port_num) + ", sd=" + str(socket_num) + "\n")

    # Listen for incoming connections
    echo_socket.listen()

    # Start accepting client connections
    while True:
        client, addr = echo_socket.accept()
        from_client = ''
        while True:
            data = client.recv(4096)
            if not data: 
                break
            print(data.decode("utf-8"))
            client.send(bytes("I am Server","utf-8"))
        client.close()
        print('client disconnected')

if __name__ == "__main__":
    main()