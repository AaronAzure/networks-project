# CITS3002 2022 Project, written by:
# Aaron Wee		(22702446)
# Daniel Ling		(22896002)
# Muhammad Maaz Ahmed	(22436686)

import select, shutil, socket, struct, subprocess, sys
import getopt, os
import time #! DELETE

BOLD = "\033[1;30m"
RED = "\033[1;31m"
BLU = "\033[1;34m"
GRN = "\033[1;32m"
YEL = "\033[1;33m"
MAG = "\033[1;35m"
CYN = "\033[1;36m"
RST = "\033[0m"

############ HARDCODE, GET RID OF THIS LATER ##################################
HOST = 'localhost'
PORT_NUM = 12345
DEFAULT_PORT = 12345
VERBOSE = False
rakefile  = 'Rakefile'	# Will be used to store rakefile.
#################################################################################

def fread(filename):
	'''
	Function that receives a filename and then returns important, stripped list of lines.
	'''
	rfile = open(filename, 'r')
	lines = rfile.readlines()
	rfile.close()
	
	count = 0
	result = []
	for line in lines:

		# skip empty lines
		if line == '\n' or line == '':
			continue

		# strip '#' and all characters after it from that line
		if line.find('#') == 0:
			continue
		elif line.find('#') > 0:
			result.append(line.split('#', 1)[0])
		else:
			result.append(line)
		
		result[count] = result[count].rstrip('\n')	# strip newline
		result[count] = result[count].rstrip()		# strip trailing whitespaces
		count += 1
	return result


def extract_info(items):
	'''
	Extract important information from @param items into a dictionary (mapping) format.	
	'''
	# Dictionary holding the port number, a 1D array of hosts and a 2D arrays of action sets.
	item_dictionary = {'Port': '', 'Hosts': []}
	
	# variables for the action set
	count = 1
	current_actionset = ''
	
	global DEFAULT_PORT
	for item in items:
		# LINE STARTS WITH PORT, SO GET AND STORE DEFAULT PORT NUMBER.
		if item.find('PORT') >= 0:
			DEFAULT_PORT = int(item.split('= ', 1)[1])
			item_dictionary['Port'] = DEFAULT_PORT
		
		# LINE STARTS WITH HOSTS, SO GET AND STORE HOST(S).
		elif item.find('HOSTS') >= 0:
			item = item.replace('HOSTS = ', '')
			item_dictionary['Hosts'] = item.split(' ', item.count(' '))
			
		# LINE STARTS WITH actionset, GET AND STORE Actionset.
		elif item.find('actionset' + str(count) + ':') >= 0:
			current_actionset = 'Action Set ' + str(count)
			item_dictionary[ current_actionset ] = []
			count += 1
		
		# STORE ACTION.
		elif item.count('\t') == 1 and item != '\t':
			action = item.strip()
			if len(action) > 0:
				item_dictionary[ current_actionset ].append( [action] )
		
		# STORE REQUIREMENTS FOR PREVIOUS ACTION.
		elif item.count('\t') == 2 and len(item_dictionary[ current_actionset ]) > 0:
			req_file = item.strip()
			if len(req_file) > 0:
				item_dictionary[ current_actionset ][-1].append( req_file )
		
	# All hosts with no specified port number get assigned the default port number.
	count = 0
	for host in item_dictionary.get('Hosts'):
		if host.find(':') >= 0:
			item_dictionary['Hosts'][count] = (host.split(':', 1)[0], int(host.split(':', 1)[1]))
		elif host == '':
			item_dictionary['Hosts'].remove(host)
		else:
			item_dictionary['Hosts'][count] = (host, item_dictionary['Port'])
		count += 1
			
	return item_dictionary


def get_action_set_names(rdictionary):
	'''
	Return actionsets headers.
	'''
	actionsets = []			# ACTIONSET KEYS LIST.
	action_failure = False		# IF TRUE, AN ACTION HAS FAILED. DO NOT EXECUTE NEXT ACTIONSET.
	
	for key in rdictionary:
		if key.find('Action Set ') >= 0:
			actionsets.append(key)

	return actionsets

def execute_on_server(server_port_tuple, argument, requirements=None):
	'''
	Function that performes actions that require the server. 
	Receives the action and a list of the necessary files.
	'''
	# ADDS FILE REQUIREMENTS TO arguments STRING, SEPARATED BY ' Requirements: '.
	if requirements != None:
		argument += ' Requirements:'
		for requirement in requirements:
			argument += ' '
			argument += requirement
	
	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sd.connect( server_port_tuple )
	
	# INFORMS SERVER REGARDING THE PAYLOAD SIZE
	header = struct.pack('i i', 0, len(argument))
	sd.send( header )
	
	# SENDS SERVER THE COMMAND/ACTION TO BE EXECUTED
	sd.send(bytes(argument, "utf-8"))

	# SEND FILES TO SERVER
	if requirements != None:
		for requirement in requirements:
			print(f'{BLU}> sending', requirement, RST)

			# INFORM THE SERVER THE SIZE OF THE FILE TO RECEIVE
			file_size = os.path.getsize( requirement )
			file_size_struct = struct.pack('i', file_size)
			print(f'{BLU}> filesize = {file_size}, sent as {file_size_struct}', RST)
			sd.send( file_size_struct )

			try: 
				file = open(requirement, 'rb')
				file_to_send = file.read()
				sd.send( file_to_send )
			except:
				file = open(requirement, 'r')
				file_to_send = file.read()
				sd.send(bytes(file_to_send, "utf-8"))
			
			file.close()

	return sd
	

def get_cheapest_host(hosts, argument, requirements=None):
	'''
	Simultaneously get the cost of each remote host, 
	and report back the remote host with the lowest cost
	'''
	if requirements != None:
		argument += ' Requirements: '
		for requirement in requirements:
			argument += requirement
			argument += ' '
	
	frame = struct.pack('i i', 1, len(argument))

	cheapest_host = 0
	lowest_cost = float('inf')

	for i in range(len(hosts)):
		sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sd.connect( hosts[i] )

		sd.send( frame )

		# RECEIVE THE COST FOR THE COMMAND
		reply = sd.recv(4)
		reply = struct.unpack('i', reply)
		cost = reply[0]
		
		# REMEMBER THE REMOTE HOST RETURNING THE LOWEST COST TO RUN THE COMMAND
		if cost < lowest_cost:
			lowest_cost = cost
			cheapest_host = i

	return cheapest_host
	

def read_option_flags():
	global HOST
	global VERBOSE
	global PORT_NUM
	global SOCKET_NUM
	global rakefile 

	try:
		opts, args = getopt.getopt(sys.argv[1:], "vhi:p:r:")
		
		for opt, arg in opts:
			# HELP ( HOW TO USE )
			if opt == '-h':
				print('usage: rake-p.py -i <ip address> -p <port number> -r <rakefile>')
				sys.exit()
			# IP ADDRESS
			elif opt == '-i':
				HOST = arg
			# RAKEFILE TO ANAYLSE
			elif opt == '-r':
				rakefile = arg
			# PORT NUMBER
			elif opt == "-p":
				PORT_NUM = int(arg)
			# VERBOSE - DEBUGGING
			elif opt == "-v":
				VERBOSE = True
	except getopt.GetoptError:
		print('usage: rakeserver.py -i <ip address> -p <port number> -r <rakefile>')
		sys.exit(2)

####################################################################################################

def main():
	global HOST
	global PORT_NUM
	global DEFAULT_PORT
	global VERBOSE
	global rakefile 

	# OPTION FLAGS
	read_option_flags()
	
	if VERBOSE:
		print('\n', 'Looking at this file:', rakefile)
		
	string_list = fread(rakefile)
	
	###DEBUG###
	if VERBOSE:
		print('\nThis is what was in the file:\n', string_list, '\n')

	rake_dict = extract_info(string_list)
	
	###DEBUG###
	if VERBOSE:
		print('\nDictionary:','\n', rake_dict, '\n')
	
	hosts = rake_dict['Hosts']
	actionset_names = get_action_set_names(rake_dict)

	if VERBOSE:
		print(f"hosts = {hosts}")
		print(f"actionset_names = {actionset_names}")
		start_time = time.time()
	

	# PERFORM ACTION ON SERVER ( HOSTS )
	error_in_actionset = False
	for actionset in actionset_names:

		current_action = 0
		outputs_received = 0
		total_actions = len(rake_dict[ actionset ])
		still_waiting_for_outputs = True

		inputs = []

		if VERBOSE:
			print(GRN, "--------------------------------------------------------------------------------", RST)
			print('starting', actionset)
			print(f"{GRN}{rake_dict[actionset]}{RST}")

		while still_waiting_for_outputs:
			if current_action < total_actions:
				action = rake_dict[actionset][current_action]

				if VERBOSE:
					print(f'{CYN}running {action[0]}{RST}')
				
				# CHECK IF ACTION HAS REQUIREMENTS
				requirements = None
				if len(action) > 1: # HAS REQUIREMENT FILES
					requirements = action[1].split()[1:]

				#* IF ACTION IS REMOTE, THEN CHECK COST FROM EACH REMOTE SERVER
				if action[0].find('remote-') == 0:
					argument = action[0].split("remote-")[1]

					cheapest_host = get_cheapest_host( hosts, argument, requirements) # cost simulateonusly

					# EXECUTE ON CHEAPEST REMOTE HOST
					print(f"{YEL} --- REMOTE EXECUTION --- {RST}")
					sd = execute_on_server( hosts[cheapest_host] , argument , requirements )
					print(f"{BLU}> {argument} {requirements}{RST}")
					inputs.append(sd)
			
				#* IF ACTION IS LOCAL, EXECUTE ON LOCAL SERVER
				else:
					print(f"{YEL} --- LOCAL EXECUTION --- {RST}")
					sd = execute_on_server( ( 'localhost' , DEFAULT_PORT ) , action[0], requirements )
					print(f"{BLU}> {action[0]} {requirements}{RST}")
					inputs.append(sd)

				current_action += 1
			
			if inputs:
				readable, writable, exceptional = select.select(inputs, [], inputs, 0)
				# READ FROM SERVER, WHILST CONNECTED
				for sd in readable:
					print(MAG, "----------------------------------------", RST)
					print(MAG, f"from {sd.getpeername()}", RST)
					
					mad_frame_server = sd.recv(16)	# FRAME: EXIT STATUS, FILENAME LENGTH, OUTPUT SIZE, ERROR LENGTH
					if mad_frame_server:
						frame_data 		= struct.unpack('i i i i', mad_frame_server)
						exit_status 	= frame_data[0]
						filename_len 	= frame_data[1]
						output_size 	= frame_data[2]
						err_size 		= frame_data[3]
						print(f"< status:\n{exit_status}")
						
						# NOT RECEIVING OUTPUT FILE
						if filename_len == 0:	
							output = sd.recv( output_size ).decode("utf-8")
							err = sd.recv( err_size).decode("utf-8")
							
							if output != "":
								print(f"< output:\n{output}")
							else:
								print(f"< output:\nNone")
							if err != "":
								print(f"< err:\n{err}")
							else:
								print(f"< err:\nNone")

						# RECEIVING OUTPUT FILE
						else:			
							outputname = sd.recv( filename_len ).decode("utf-8")
							output = sd.recv( output_size )
							err = sd.recv( err_size).decode("utf-8")
							
							print(f"< output file name:\n{outputname}")
							if err != "":
								print(f"< err:\n{err}")
							else:
								print(f"< err:\nNone")

							file = open(outputname, 'wb')
							file.write(output)
							file.close()
					
					if exit_status != 0:
						error_in_actionset = True
					
					sd.close()
					inputs.remove(sd)
					
					outputs_received += 1
					if outputs_received >= total_actions:
						still_waiting_for_outputs = False
					
				for sd in exceptional:
					error_in_actionset = True
					sd.close()
					inputs.remove(sd)

		if error_in_actionset:
			print(f"{RED}error detected in actionset - halting subsequent actionsets{RST}")
			break
		
	if VERBOSE:
		print(f"{YEL}----------------------------------{RST}")
		print(f"{YEL}  EXECUTION TIME = {(time.time() - start_time):.2f}s{RST}")
		print(f"{YEL}----------------------------------{RST}")
		
if __name__ == "__main__":
	main()
