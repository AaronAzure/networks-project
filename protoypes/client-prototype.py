import os
import sys
import socket

def main():
	server_addr = ('localhost', 12345)
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
		s.connect(server_addr)
		# s.send(b"Hello, world")
		s.send(bytes("Hello, world", "utf-8"))
		data = s.recv(1024)
		if data:
			print(data.decode("utf-8"))

if __name__ == "__main__":
    main()