import socket
import sys, getopt
import os

# port number
HOST = 'localhost'
PORT_NUM = 12345
SOCKET_NUM = 0
VERBOSE = False

BOLD = "\033[1;30m"
RED = "\033[1;31m"
GRN = "\033[1;32m"
YEL = "\033[1;33m"
MAG = "\033[1;35m"
CYN = "\033[1;36m"
RST = "\033[0m"



def main():
    global HOST
    global VERBOSE
    global PORT_NUM
    global SOCKET_NUM

    try:
        opts, args = getopt.getopt(sys.argv[1:], "vhi:p:")
        
        for opt, arg in opts:
            # HELP ( HOW TO USE )
            if opt == '-h':
                print('usage: rakeserver.py -p <port number>')
                sys.exit()
            # IP ADDRESS
            elif opt == '-i':
                HOST = int(arg)
            # PORT NUMBER
            elif opt == "-p":
                PORT_NUM = int(arg)
            # VERBOSE - DEBUGGING
            elif opt == "-v":
                VERBOSE = True
    except getopt.GetoptError:
        print('usage: rakeserver.py -i <ip address> -p <port number>')
        sys.exit(2)


    # A TCP based echo server
    sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 
    # Bind the IP address and the port number
    sd.bind((HOST, PORT_NUM))
    
    SOCKET_NUM = 0
    # local_ip = socket.gethostbyname("localhost")
    if VERBOSE:
        print("IP address = " + HOST)
    print(MAG + "listening on port=" + str(PORT_NUM) + ", sd=" + str(SOCKET_NUM) + RST)
    print("---------------------------------------------")

    # Listen for incoming connections
    sd.listen()

    # Start accepting client connections
    while True:
        client, addr = sd.accept() #! BLOCKING
        SOCKET_NUM += 1
        print(BOLD + " Accepted new client on sd=" + str(SOCKET_NUM) + RST)
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
        print(BOLD + ' Client disconnected from sd=' + str(SOCKET_NUM) + '\n' + RST)
        SOCKET_NUM -= 1
        print(MAG + "listening on port " + str(PORT_NUM) + ", sd " + str(SOCKET_NUM) + RST)
        print("----------------------------------------")

    

if __name__ == "__main__":
    main()
