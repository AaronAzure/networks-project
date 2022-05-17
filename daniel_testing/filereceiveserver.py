import socket
import sys, getopt
import os, subprocess
import random
import tempfile, shutil

import time #! DELETE

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



def cost_for_execution():
	'''
	Returns the cost of executing a command on this server. 
	So that the client chooses the server making the lowest 'bid', 
	and will then (next) ask that server to execute the command. 
	'''
	return random.randint(1, 100)

def read_option_flags():
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
				HOST = arg
			# PORT NUMBER
			elif opt == "-p":
				PORT_NUM = int(arg)
			# VERBOSE - DEBUGGING
			elif opt == "-v":
				VERBOSE = True
	except getopt.GetoptError:
		print('usage: rakeserver.py -i <ip address> -p <port number>')
		sys.exit(2)


def main():
	global HOST
	global VERBOSE
	global PORT_NUM
	global SOCKET_NUM

	read_option_flags()

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
			data = client.recv(1024)     #! BLOCKING
			# RECEIVED DATA FROM A CLIENT
			if data: 
				#time.sleep(1)	#! DELETE
				data = data.decode("utf-8")
				
				#* CLIENT ASKING FOR QUOTE/COST FOR EXECUTING COMMAND
				if data == "cost?":
					cost = cost_for_execution()
					print("- cost =", cost)
					client.send(bytes( f"{cost}" , "utf-8"))
					continue

				# DECODE RECEIVED DATA
				data = data.split(' Requirements:')
				arguments = data[0].split()		# STORES ARGUMENTS AS A LIST.
				requirements = []			# STORES INPUT FILE(S) AS A LIST.
				server_dir = os.getcwd()		# SERVER DIRECTORY
				input_dir = tempfile.mkdtemp()		# TEMPORARY DIRECTORY FOR INPUT FILE(S)
				output_dir = tempfile.mkdtemp()		# TEMPORARY DIRECTORY FOUR OUTPUT FILE(S)
				os.chdir(output_dir)			# CHANGE WORKING DIRECTORY TO output_dir.
				
				if VERBOSE:
					print('arguments:', arguments, '\nrequirements:', requirements)
						
				# INFORM CLIENT THAT IT HAS RECEIVED THE DATA
				client.send(bytes(f"Server received {data}", "utf-8"))
				
				# RECEIVE AND INFORM CLIENT IT HAS RECEIVED NECESSARY FILES
				if len(data) == 2:
					
					requirements = data[1].split()
					
					print(requirements)	# DEBUG: PRINTS THE REQUIRED FILE AND ITS SIZE
								# SEPARATED BY '='
					
					# USING GCC TO SPECIFICALLY COMPILE THE OUTPUT FILE IN THE TEMPORARY DIRECTORY.
					#arguments[0] = 'gcc'
					#arguments.append('&)
					#arguments.append(mv)
					
					#shutil.rmtree(temporary_directory)
					for requirement in requirements:
						rfile = requirement.split('=')
						
						count = 0
						for argument in arguments:
							print('finding', argument)
							print ('current file is', input_dir + '/' + rfile[0])
							if argument == rfile[0]:
								arguments[count] = input_dir + '/' + rfile[0]
								print ('new argument location:', argument)
							count += 1
							
						# READ BINARY FILE
						if '.o' in rfile[0]:
							file = open(input_dir + '/' + rfile[0], "wb")
							data = client.recv(int(rfile[1]))
						
						# READ ASCII TEXT FILE (I THINK)
						else:
							file = open(input_dir + '/' + rfile[0], "w")
							data = client.recv(int(rfile[1])).decode("utf-8")
							
						file.write(data)
						file.close()
						
						# INFORMING THE CLIENT THAT THE FILE HAS BEEN RECEIVED
						client.send(bytes(f"{rfile[0]} file of size {rfile[1]} received\n", "utf-8"))
				
				# EXECUTES COMMAND
				print(arguments)
				execution = subprocess.run(arguments, capture_output = True)
				return_code = '\n\tExit status: ' + str(execution.returncode)
				
				if not execution.stdout.decode() == '':
					return_code += '\n\tOutput:\n' + execution.stdout.decode()
					
				elif not execution.stderr.decode() == '':
					return_code += '\n\tError:\n' + execution.stderr.decode()
					
				print("return value = " + str(return_code))
				
				# INFORM CLIENT THE RETURN STATUS OF EXECUTING THE COMMAND
				client.send(bytes(str(return_code), "utf-8"))
				
				# INFORM CLIENT OF ANY OUTPUT FILES.
				if not requirements == []:
					 files = os.listdir(output_dir)	
					 filesize = os.path.getsize(files[0])
					 message = files[0] + '=' + str(filesize)
					 client.send(bytes(message, "utf-8"))
					 
					 file = open(files[0], 'rb')
					 reading_file = file.read()
					 client.send(reading_file)
					 file.close()
				
				os.chdir(server_dir)
				shutil.rmtree(input_dir)
				shutil.rmtree(output_dir)
				
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
