import socket
import sys, getopt
import os, subprocess
import random
import struct
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
BLU = "\033[1;34m"
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


def find_file(filename):
	'''
	Function to find a file path in the working directory.
	''' 
	for root, dirs, files in os.walk(os.getcwd()):
		if filename in files:
			print(os.path.join(root, filename))
			return os.path.join(root, filename)
	return filename


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


def convert_filepath_to_local(files):
	
	result = files
	for i in range(len(result)):
		result[i] = result[i].split('/')[-1]

	return result


def main():
	global HOST
	global VERBOSE
	global PORT_NUM
	global SOCKET_NUM

	read_option_flags()

	# A TCP-based server
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
			data = client.recv(8)     #! BLOCKING
			if data != None:
				# DECRYPT HEADER
				header = struct.unpack('i i', data)
				asking_for_cost = bool(header[0])
				command_length = header[1]

				if asking_for_cost:
					quote = cost_for_execution()
					cost_response = struct.pack('i', quote)
					print("> cost =", quote)
					client.send( cost_response )
					client.close()
					data = None
					break

				# RECEIVE THE COMMAND + REQUIREMENTS
				data = client.recv( command_length )     #! BLOCKING
				payload = data.decode("utf-8")
				
				#* CLIENT ASKING FOR QUOTE/COST FOR EXECUTING COMMAND

				# DECODE RECEIVED DATA
				pid = os.fork()
				# CHILD PROCESS DEALS WITH CURRENT ACTION
				if pid == 0:
					payload = payload.split(' Requirements:')
					arguments = payload[0].split()	# STORES ARGUMENTS AS A LIST.
					arguments = convert_filepath_to_local( arguments )

					requirements = []				# STORES INPUT FILE(S) AS A LIST.
					input_dir = None				# TEMPORARY DIRECTORY FOR INPUTS
					output_dir = None				# TEMPORARY DIRECTORY FOR OUTPUTS

					if len(payload) == 2:
						requirements = payload[1].split()
						requirements = convert_filepath_to_local( requirements )

					if VERBOSE:
						print('< arguments:', arguments, '\n< requirements:', requirements)
					
					# SERVER DIRECTORY
					server_dir = os.getcwd()		
					
					input_dir = tempfile.mkdtemp()	# TEMPORARY DIRECTORY FOR INPUT FILE(S)
					output_dir = tempfile.mkdtemp()	# TEMPORARY DIRECTORY FOUR OUTPUT FILE(S)
					os.chdir( input_dir )			# CHANGE WORKING DIRECTORY TO input_dir.

					# THERE ARE REQUIREMENTS
					if len(requirements) > 0:
						print(f"{BLU}input_dir  = {input_dir}{RST}")
						print(f"{BLU}output_dir = {output_dir}{RST}")
						
						# RECEIVE EACH REQUIRED FILE
						for required_file in requirements:
						
							# GET THE SIZE OF THE FILE TO BE RECEIVED FROM THE CLIENT
							reply = client.recv(4)
							data_size = struct.unpack('i', reply)
							file_to_recv_size = data_size[0]

							# todo - RECEIVE THE SIZE OF FILE TO RECV
							
							# READ BINARY FILE
							try:
								file = open(required_file, "wb")
								file_data = client.recv( file_to_recv_size )
							# READ TEXT FILE
							except:
								file = open(required_file, "w")
								file_data = client.recv( file_to_recv_size ).decode("utf-8")
								
							file.write( file_data )
							file.close()

							# TRANSLATE FILE LOCATION WITH RESPECT TO SERVER DIRECTORY
							for i in range(len(arguments)):
								if arguments[i] == required_file:
									arguments[i] = input_dir + '/' + required_file
							
					os.chdir( output_dir )			# CHANGE WORKING DIRECTORY TO output_dir.

					# EXECUTES COMMAND
					# execution = subprocess.run(arguments, capture_output=True)
					# todo - print(f"{YEL}EXECUTING = {arguments}{RST}")
					execution = subprocess.run(' '.join(arguments), capture_output=True, shell=True)

					# INFORM CLIENT OF ANY OUTPUT FILES.
					
					n_output_files_created = [f for f in os.listdir( output_dir ) if os.path.isfile(os.path.join(output_dir, f))]
					# NO OUTPUT FILES.
					if len(n_output_files_created) == 0:	# Non-compiling action executed.
						# INFORM CLIENT THE RETURN STATUS OF EXECUTING THE COMMAND
						exit_status = execution.returncode
				
						# INFORM CLIENT THE RETURN OUTPUT OF EXECUTING THE COMMAND
						if exit_status == 0 and execution.stdout != None:
							output = execution.stdout.decode("utf-8")
						elif exit_status != 0 and execution.stderr != None:
							output = execution.stderr.decode("utf-8")

						output_status = struct.pack('i i i', exit_status, 0, len(output))
						print(f"> stat={execution.returncode}, len={len(output)}")
						client.send( output_status )


						#! time.sleep( os.getpid() % 10 * 0.1) # AVOID CRASHES
						print(f"> out={output}")
						client.send(bytes(output, "utf-8"))
						
					# HAS OUTPUT FILES.
					else:
						#########
						exit_status = execution.returncode

						onlyfiles = [f for f in os.listdir( output_dir ) if os.path.isfile(os.path.join(output_dir, f))]
						input_files = [f for f in os.listdir( input_dir ) if os.path.isfile(os.path.join(input_dir, f))]
						print(f"{RED} {onlyfiles}",RST)
						print(f"{GRN} {input_files}",RST)

						files = os.listdir( output_dir )
						filenamelength = len(files[0])
						filesize = os.path.getsize(files[0])
						
						print(f"> stat={exit_status}, filesize={filesize}")
						try:
							file = open(files[0], 'rb')
							reading_file = file.read()
						except:
							file = open(files[0], 'r')
							reading_file = file.read()
						
						#########
						print(f"> stat={exit_status}, filesize={filesize}")
						header = struct.pack('i i i', exit_status, filenamelength, filesize)
						# print("Header with a file output:", header)
						# print("Funny header size:", struct.calcsize('iii'))
						client.send(header)
						
						client.send(bytes(files[0],"utf-8"))

						client.send(reading_file)
						file.close()
					
					# # INFORM CLIENT THE RETURN STATUS OF EXECUTING THE COMMAND
					# exit_status = execution.returncode
			
					# # INFORM CLIENT THE RETURN OUTPUT OF EXECUTING THE COMMAND
					# if exit_status == 0 and execution.stdout != None:
					# 	output = execution.stdout.decode("utf-8")
					# elif exit_status != 0 and execution.stderr != None:
					# 	output = execution.stderr.decode("utf-8")

					# output_status = struct.pack('i i', exit_status, len(output))
					# print(f"> stat={execution.returncode}, len={len(output)}")
					# client.send( output_status )

					# #! time.sleep( os.getpid() % 10 * 0.1) # AVOID CRASHES
					# print(f"> out={output}")
					# client.send(bytes(output, "utf-8"))
				
					# CHANGE BACK TO ORIGINAL DIRECTORY
					os.chdir(server_dir)

					# todo - DELETE ANY TEMP DIRECTORIES
					if input_dir:
						print(f"{YEL} - DELETING FILES - {RST}")
						shutil.rmtree( input_dir )
					if output_dir:
						print(f"{YEL} - DELETING FILES - {RST}")
						shutil.rmtree( output_dir )

					client.close()
					print(BOLD + ' Client disconnected from sd=' + str(SOCKET_NUM) + '\n' + RST)
					SOCKET_NUM -= 1
					print(MAG + "listening on port " + str(PORT_NUM) + ", sd " + str(SOCKET_NUM) + RST)
					print("----------------------------------------")
					sys.exit( exit_status )

				# PARENT PROCESS LISTENS FOR OTHER CLIENT REQUEST(S)
				else:
					data = None
					print("created a child process to execute command")
					break
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
