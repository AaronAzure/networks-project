# CITS3002 2022 Project, written by:
# Muhammad Maaz Ahmed	(22436686)
# Aaron Wee				(22702446)
# Daniel Ling			(22896002)

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

DEFAULT_PORT = 12345
VERBOSE = False
rakefile  = 'Rakefile'	# Will be used to store rakefile.

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


def execute_on_server(server_port_tuple, argument, requirements=[]):
	'''
	Function that performes actions that require the server. 
	Receives the action and a list of the necessary files.
	'''
	
	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sd.connect( server_port_tuple )
	
	header = struct.pack('i i i', 0, len(argument), len(requirements))
	sd.send( header )
	
	# SENDS SERVER THE COMMAND/ACTION TO BE EXECUTED
	sd.send(bytes(argument, "utf-8"))

	# SEND FILES TO SERVER
	if requirements != None:
		for requirement in requirements:
			print(f'{BLU}> sending', requirement, RST)

			# INFORM THE SERVER THE LENGTH OF THE FILE NAME AND SIZE OF THE FILE TO RECEIVE
			file_size = os.path.getsize( requirement )
			file_name_length = len(requirement)
			file_struct = struct.pack('i i i', 0, file_name_length, file_size)

			print(f'{BLU}> filesize = {file_size}, file name length = {file_name_length}, sent as {file_struct}', RST)
			sd.send( file_struct )
			
			file = open(requirement, 'rb')
			file_to_send = file.read()
			sd.send( file_to_send )

			sd.send( bytes(requirement, 'utf-8') )				# SENDING FILE NAME.
			
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
	
	frame = struct.pack('i i i', 1, len(argument), 0)

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
	global VERBOSE
	global SOCKET_NUM
	global rakefile 

	try:
		opts, args = getopt.getopt(sys.argv[1:], "vhr:")
		
		for opt, arg in opts:
			# HELP ( HOW TO USE )
			if opt == '-h':
				print('usage: rake-p.py -i <ip address> -r <rakefile>')
				sys.exit()
			# RAKEFILE TO ANAYLSE
			elif opt == '-r':
				rakefile = arg
			# VERBOSE - DEBUGGING
			elif opt == "-v":
				VERBOSE = True
	except getopt.GetoptError:
		print('usage: rakeserver.py -i <ip address> -r <rakefile>')
		sys.exit(2)

####################################################################################################

def main():
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
				requirements = []
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
					
					exit_status = 1
					
					# SERVER TO CLIENT FRAME: EXIT STATUS, OUTPUT LENGTH, OUTPUT FILE SIZE
					#                         OUTPUT FILE NAME LENGTH, ERROR LENGTH
					mad_frame_server = sd.recv(20)
					if mad_frame_server:
						frame_data = struct.unpack('i i i i i', mad_frame_server)
						exit_status 			= frame_data[0]
						output_len 				= frame_data[1]
						output_filesize 		= frame_data[2]
						output_filename_length 	= frame_data[3]
						error_len 				= frame_data[4]
						
						print(f"< status:\n{exit_status}")

						if output_len > 0:
							output = sd.recv( output_len ).decode("utf-8")
							print("< stdout:")
							print(output, file=sys.stdout)
						else:
							print("< stdout:")
							print("", file=sys.stdout)

						if error_len > 0:
							err = sd.recv( error_len ).decode("utf-8")
							print("< stderr:")
							print(err, file=sys.stderr)
						else:
							print("< stderr:")
							print("", file=sys.stderr)

						# RECEIVING OUTPUT FILE
						if output_filesize > 0 and output_filename_length > 0:			
							output_file = sd.recv( output_filesize )
							output_filename = sd.recv( output_filename_length ).decode("utf-8")

							file = open(output_filename, 'wb')
							file.write(output_file)
							file.close()
							
							print(f"< output file name:\n{output_filename}")
						
					
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

		time.sleep(1)
		
	if VERBOSE:
		print(f"{YEL}----------------------------------{RST}")
		print(f"{YEL}  EXECUTION TIME = {(time.time() - start_time):.2f}s{RST}")
		print(f"{YEL}----------------------------------{RST}")
		
if __name__ == "__main__":
	main()
