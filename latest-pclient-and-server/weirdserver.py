# CITS3003 2022 Project, written by:
# Aaron Wee		(22702446)
# Daniel Ling		(22896002)
# Muhammad Maaz Ahmed	(22436686)

import shutil, socket, struct, subprocess, sys
import getopt, os, random, tempfile
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


def find_output_file(directory, latest_update):
	'''
	Function is given the latest file modification time prior to action execution. 
	Function then finds the output file in the temporary directory. If there are no files
	that exceed latest_update, then None is returned.
	''' 
	
	if latest_update == 0.0:	# NO FILE IN TEMPORARY DIRECTORY.
		return None
		
	all_files = [f for f in os.listdir( directory ) if os.path.isfile(os.path.join(directory, f))]
	
	for f in all_files:
		if os.path.getmtime(os.path.join(directory, f)) > latest_update:
			return f

	return None


def read_option_flags():
	'''
	Function that reads option flags at the command line.
	'''
	
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
	'''
	Function that takes files with directory paths from the client and 
	strips them down to the filename
	'''
	
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

				# CLIENT ASKING FOR QUOTE/COST FOR EXECUTING COMMAND
				if asking_for_cost:
					quote = cost_for_execution()
					cost_response = struct.pack('i', quote)
					print("> cost =", quote)
					client.send( cost_response )
					client.close()
					data = None
					break

				# RECEIVE THE COMMAND + REQUIREMENTS
				data = client.recv( command_length )	#! BLOCKING
				payload = data.decode("utf-8")		# DECODE RECEIVED DATA
				
				pid = os.fork()
				# CHILD PROCESS DEALS WITH CURRENT ACTION
				if pid == 0:
					payload = payload.split(' Requirements:')
					arguments = payload[0].split()	# STORES ARGUMENTS AS A LIST.
					arguments = convert_filepath_to_local( arguments )
					requirements = []		# STORES INPUT FILE(S) AS A LIST.
					latest_update = 0.0		# STORES TIME OF LATEST UPDATED FILE.

					if len(payload) == 2:
						requirements = payload[1].split()
						requirements = convert_filepath_to_local( requirements )

					if VERBOSE:
						print('< arguments:', arguments, '\n< requirements:', requirements)
					
					# SERVER DIRECTORY
					server_dir = os.getcwd()	# SERVER DIRECTORY	
					temp_dir = tempfile.mkdtemp()	# TEMPORARY DIRECTORY FOR ALL FILES.
					os.chdir(temp_dir)

					# THERE ARE REQUIREMENTS
					if len(requirements) > 0:
						print(f"{BLU} - TEMPORARY DIRECTORY: {temp_dir} - {RST}")
					
						# RECEIVE EACH REQUIRED FILE
						for required_file in requirements:
						
							# GET THE SIZE OF THE FILE TO BE RECEIVED FROM THE CLIENT
							reply = client.recv(4)
							data_size = struct.unpack('i', reply)
							file_to_recv_size = data_size[0]

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
							
							# STORES MODIFIED TIME OF FILE IF IT EXCEEDS latest_update.
							if latest_update < os.path.getmtime(os.path.join(temp_dir, required_file)):
								latest_update = os.path.getmtime(os.path.join(temp_dir, required_file))

					# EXECUTES COMMAND
					execution = subprocess.run(' '.join(arguments), capture_output=True, shell=True)

					# INFORM CLIENT OF ANY OUTPUT FILES.
					output_file = find_output_file(temp_dir, latest_update)
					
					# NO OUTPUT FILES.
					if output_file == None:	# Non-compiling action executed.
						exit_status = execution.returncode		# OUTPUT RETURN CODE.
						output = execution.stdout.decode("utf-8")	# OUTPUT.
						err = execution.stderr.decode("utf-8")		# OUTPUT ERROR MESSAGE.

						header = struct.pack('i i i i', exit_status, 0, len(output), len(err))
						print(f"> stat={execution.returncode}, output len={len(output)}, err len={len(err)}")
						client.send(header)

						print(f"> out={output}")
						client.send(bytes(output, "utf-8"))
						
						print(f"> err={err}")
						client.send(bytes(err, "utf-8"))
						
					# HAS OUTPUT FILES.
					else:
						exit_status = execution.returncode		# OUTPUT RETURN CODE.
						err = execution.stderr.decode("utf-8")		# OUTPUT ERROR MESSAGE	.

						input_files = [f for f in os.listdir( temp_dir ) if os.path.isfile(os.path.join(temp_dir, f))]
						input_files.remove(output_file)
						
						print(f"{RED} output file = {output_file}",RST)
						print(f"{GRN} input files = {input_files}",RST)

						filenamelength = len(output_file)
						filesize = os.path.getsize(output_file)
						
						try:
							file = open(output_file, 'rb')
							reading_file = file.read()
						except:
							file = open(output_file, 'r')
							reading_file = file.read()
	
						print(f"> stat={exit_status}, filesize={filesize}, errsize={len(err)}")
						print(f"> err={err}")
						
						header = struct.pack('i i i i', exit_status, filenamelength, filesize, len(err))
						
						client.send(header)
						client.send(bytes(output_file,"utf-8"))
						client.send(reading_file)
						client.send(bytes(err, "utf-8"))
						
						file.close()
					
					# CHANGE BACK TO ORIGINAL DIRECTORY
					os.chdir(server_dir)

					# DELETE ANY TEMP DIRECTORIES
					if temp_dir:
						print(f"{YEL} - DELETING FILES - {RST}")
						shutil.rmtree( temp_dir )

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
