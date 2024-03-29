# CITS3003 2022 Project, written by:
# Muhammad Maaz Ahmed	(22436686)
# Aaron Wee		(22702446)
# Daniel Ling		(22896002)

import shutil, socket, struct, subprocess, sys
import getopt, os, random, tempfile, time

HOST		= 'localhost'
PORT_NUM	= 12345
VERBOSE		= False

BOLD 	= "\033[1;30m"
RED 	= "\033[1;31m"
GRN 	= "\033[1;32m"
YEL 	= "\033[1;33m"
BLU 	= "\033[1;34m"
MAG 	= "\033[1;35m"
CYN 	= "\033[1;36m"
RST 	= "\033[0m"

def send_cost(client):
	'''
	Sends the cost of executing an action on this server to the client.
	'''
	quote = random.randint(1, 100)
	cost_response = struct.pack('i', quote)
	print("> cost =", quote)
	client.send( cost_response )
	client.close()

def find_output_file(directory, latest_update):
	''' 
	Function finds the output file in the temporary directory. @param directory is the 
	working directory. latest_update is the latest modification time of any files in 
	the working directory. @returns the file whose modification time exceeds latest_update.
	None otherwise.
	''' 
	if latest_update == 0.0:	# NO FILE IN TEMPORARY DIRECTORY.
		return None
		
	all_files = [f for f in os.listdir( directory ) if os.path.isfile(os.path.join(directory, f))]
	
	for f in all_files:
		if os.path.getmtime(os.path.join(directory, f)) > latest_update:
			return f
	return None

def get_req_files(requirement_length, client, latest_update):
	'''
	Server prepares to receive files and write them into the temporary directory.  
	@param requirement_length is the number of files required for the action, 
	client is client communicating witht he server, latest_update is the latest 
	modification time of any files in the working directory. @returns the latest
	modification time of the last modified file in the working directory.
	'''
	# RECEIVE EACH REQUIRED FILE
	for i in range(requirement_length):
		req_file_data = client.recv(12)     #! BLOCKING

		# DECRYPT HEADER
		if req_file_data:
			req_file_header = struct.unpack('i i i', req_file_data)
			if VERBOSE:
				print(f"{YEL}{req_file_header}{RST}")
			
			filename_length = req_file_header[1]
			file_to_recv_size = req_file_header[2]

			file_data = client.recv( file_to_recv_size )
			
			# GET THE NAME OF THE FILE TO BE RECEIVED FROM THE CLIENT
			filename = client.recv( filename_length ).decode("utf-8")

			if VERBOSE:
				print(f"--|{filename}|--")
				print(f"creating file {filename}")
			
			# CREATE FILE AND WRITE DATA TO IT
			file = open(filename, "wb")
			file.write( file_data )
			file.close()
		
			# STORES MODIFIED TIME OF FILE IF IT EXCEEDS latest_update.
			if latest_update < os.path.getmtime( filename ):
				latest_update = os.path.getmtime( filename )
	
	return latest_update

def send_output(execution, client, temp_dir, output_file):
	'''
	Multi-step process to send output back to the client. First sends a frame header. 
	Then sends output, error or file and file name (if any exists). @param execution is 
	the executed action, client is the client communicating with the server, temp_dir is 
	the directory where any files for the current action are located, output_file is the 
	file to be sent back to the client, if it exists. @returns exit status of execution.
	'''
	# PREPARING TO SEND SERVER TO CLIENT HEADER.
	exit_status = execution.returncode		# OUTPUT RETURN CODE.
	output = execution.stdout.decode("utf-8")	# OUTPUT.
	filesize = 0					# OUTPUT FILE SIZE.
	filename_length = 0				# OUTPUT FILE NAME LENGTH.
	err = execution.stderr.decode("utf-8")		# OUTPUT ERROR MESSAGE.
	
	if output_file != None:				# OUTPUT FILE EXISTS.
		filesize = os.path.getsize(output_file)
		filename_length = len(output_file)

	header = struct.pack('i i i i i', exit_status, len(output), filesize, filename_length, len(err))

	print(f"> stat={execution.returncode}, output len={len(output)}, file size={filesize}, file name length={filename_length}, err len={len(err)}")
	client.send(header)

	print(f"{BLU}> out={RST}{output}")
	if len(output) > 0:
		client.send(bytes(output, "utf-8"))
		
	print(f"{RED}> err={RST}{err}")
	if len(err) > 0:
		client.send(bytes(err, "utf-8"))

	if output_file != None:				# OUTPUT FILE EXISTS.
		
		file = open(output_file, 'rb')
		reading_file = file.read()
			
		client.send(reading_file)
		
		print(f"> file={output_file}")
		client.send(bytes(output_file, "utf-8"))
		
		file.close()
		
		if VERBOSE:
			input_files = [f for f in os.listdir( temp_dir ) if os.path.isfile( f )]
			input_files.remove( output_file )
			print(f"{RED} output file = {output_file}",RST)
			print(f"{GRN} input files = {input_files}",RST)

	return exit_status

def read_option_flags():
	'''
	Function that reads option flags at the command line.
	'''
	
	global HOST
	global VERBOSE
	global PORT_NUM
	
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

	read_option_flags()

	# A TCP-based server
	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	# Bind the IP address and the port number
	sd.bind((HOST, PORT_NUM))
	
	if VERBOSE:
		print("IP address = " + HOST)
	print(MAG + "listening on port " + str(PORT_NUM) + RST)
	print("---------------------------------------------")

	# Listen for incoming connections
	sd.listen()

	# Start accepting client connections
	while True:
		client, addr = sd.accept() #! BLOCKING
		print(BOLD + " Accepted new client" + RST)
		
		while True: 
			data = client.recv(12)     #! BLOCKING
			if data != None:
				# DECRYPT HEADER
				header = struct.unpack('i i i', data)
				asking_for_cost 	= bool(header[0])
				command_length 		= header[1]
				requirement_length 	= header[2]

				# CLIENT ASKING FOR QUOTE/COST FOR EXECUTING COMMAND
				if asking_for_cost:
					send_cost(client)
					data = None
					break

				pid = os.fork()

				# CHILD PROCESS DEALS WITH CURRENT ACTION
				if pid == 0:
					time.sleep(os.getpid() % 5 * 0.1)

					argument = client.recv( command_length ).decode("utf-8")	#! BLOCKING
				
					if VERBOSE:
						print(f"< {header}")

					latest_update = 0.0		# STORES TIME OF LATEST UPDATED FILE.

					if VERBOSE:
						print(f'{GRN}< argument:', argument, RST)
					
					server_dir = os.getcwd()	# SERVER DIRECTORY	
					temp_dir = tempfile.mkdtemp()	# TEMPORARY DIRECTORY FOR ALL FILES.
					os.chdir(temp_dir)
					if VERBOSE:
						print(f"{BLU} - TEMPORARY DIRECTORY: {temp_dir} - {RST}")

					if requirement_length > 0:	# THERE ARE REQUIREMENTS
						latest_update = get_req_files(requirement_length, client, latest_update)

					if VERBOSE:
						print(f"{CYN} -- EXECUTING COMMAND --{RST}")

					# EXECUTES COMMAND
					execution = subprocess.run(argument, capture_output=True, shell=True)

					# INFORM CLIENT OF ANY OUTPUT FILES.
					output_file = find_output_file(temp_dir, latest_update)

					# SENDING THE OUTPUT BACK TO THE CLIENT, ALSO GETTING exit_status.
					exit_status = send_output(execution, client, temp_dir, output_file)
					
					os.chdir(server_dir)
					if temp_dir:
						shutil.rmtree( temp_dir )

					client.close()
					print(BOLD + ' Client disconnected' + '\n' + RST)
					print(MAG + "listening on port " + str(PORT_NUM) + RST)
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
		print(BOLD + ' Client disconnected' + '\n' + RST)
		print(MAG + "listening on port " + str(PORT_NUM) + RST)
		print("----------------------------------------")

if __name__ == "__main__":
	main()
