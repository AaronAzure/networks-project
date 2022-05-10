import socket
import sys, getopt
import os

# port number
port_num = 12345
socket_num = 0

BOLD = "\033[1;30m"
RED = "\033[1;31m"
GRN = "\033[1;32m"
YEL = "\033[1;33m"
MAG = "\033[1;35m"
CYN = "\033[1;36m"
RST = "\033[0m"


def main():
    global port_num
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hp:")
        
        for opt, arg in opts:
            if opt == '-h':
                print('usage: rakeserver.py -p <port number>')
                sys.exit()
            elif opt == "-p":
                port_num = int(arg)
    except getopt.GetoptError:
        print('usage: rakeserver.py -p <port number>')
        sys.exit(2)


    # A TCP based echo server
    echo_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
    # Bind the IP address and the port number
    host = socket.gethostbyname("localhost")
    echo_socket.bind((host, port_num))

    socket_num = 0
    # local_ip = socket.gethostbyname("localhost")
    print("IP address = " + host)
    print(MAG + "listening on port=" + str(port_num) + ", sd=" + str(socket_num) + RST)
    print("---------------------------------------------")

    # Listen for incoming connections
    echo_socket.listen()

    # Start accepting client connections
    while True:
        client, addr = echo_socket.accept() #! BLOCKING
        socket_num += 1
        print(BOLD + " Accepted new client on sd=" + str(socket_num) + RST)
        while True:
            data = client.recv(2048)     #! BLOCKING
            # RECEIVED DATA FROM A CLIENT
            if data: 
                # DECODE RECEIVED DATA
                data = data.decode("utf-8")
                print(f"{CYN} <-- {data}{RST}")
                # print(CYN + " <-- " + data + RST)
                
                # INFORM CLIENT THAT IT HAS RECEIVED THE DATA
                client.send(bytes("Received {" + data + "}", "utf-8"))
                
                # EXECUTES COMMAND
                return_code = os.system(data)
                print("return value = " + str(return_code))
                
                # INFORM CLIENT THE RETURN STATUS OF EXECUTING THE COMMAND
                client.send(bytes(str(return_code), "utf-8"))
                data = None
            # FINISHED RECEIVING DATA FROM CLIENT
            else:
                break
        client.close()
        print(BOLD + ' Client disconnected from sd=' + str(socket_num) + '\n' + RST)
        socket_num -= 1
        print(MAG + "listening on port " + str(port_num) + ", sd " + str(socket_num) + RST)
        print("----------------------------------------")

    

if __name__ == "__main__":
    main()
