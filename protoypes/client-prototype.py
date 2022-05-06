import os
import sys
import socket

def main():
	server_addr = ('localhost', 12345)
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_desc:
		sock_desc.connect(server_addr)
		# sock_desc.send(b"Hello, world")
		sock_desc.send(bytes("Hello, world", "utf-8"))
		data = sock_desc.recv(2048)
		if data:
			print(data.decode("utf-8"))

if __name__ == "__main__":
    main()