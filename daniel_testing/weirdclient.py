# CITS3003 2022 Project, written by:
# Aaron Wee		(22702446)
# Daniel Ling		(22896002)
# Muhammad Maaz Ahmed	(22436686)

import os, getopt
import subprocess
import sys
import select
import socket
import struct
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
	Extract important information from @param items into a dictionary (mapping) format
	Function that converts all items in a list to a dictionary, which is then returned.	
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
	Return actionsets headers
	'''
	actionsets = []		# List holding all the action sets.
	action_failure = False		# If True, then do not execute the next actionset.
	
	for key in rdictionary:
		if key.find('Action Set ') >= 0:
			actionsets.append(key)

	return actionsets


def file_path(filename):
	'''
	Function to find a file path in the working directory.
	'''
	for r, d, f in os.walk(os.getcwd()):
		if filename in f:
			return os.path.join(r, filename)
	return None

	
# def send_command_to_server(sd, argument, requirements=None):
# 	'''
# 	Function that performes actions that require the server. 
# 	Receives the action and a list of the necessary files.
# 	'''
# 	# If there are file requirements, add them as a string to arguments, seperated by ' Requirements: '.
# 	# Additionally, these files will need to be sent to the server as well. Meaning the server
# 	# must also know the size of the file in the case it exceeds 1024 bytes.
# 	n_req_files = 0
# 	if requirements != None:
# 		argument += ' Requirements: '
# 		for requirement in requirements:
# 			argument += requirement
# 			argument += ' '
# 			n_req_files += 1
	
# 	# INFORMS SERVER THE STRUCT
# 	header = struct.pack('i i', 0, len(argument))
# 	sd.send( header )
	
# 	# SENDS SERVER THE COMMAND/ACTION TO BE EXECUTED
# 	sd.send(bytes(argument, "utf-8"))


def execute_on_server(server_port_tuple, argument, requirements=None):
	'''
	Function that performes actions that require the server. 
	Receives the action and a list of the necessary files.
	'''
	# If there are file requirements, add them as a string to arguments, seperated by ' Requirements: '.
	# Additionally, these files will need to be sent to the server as well. Meaning the server
	# must also know the size of the file in the case it exceeds 1024 bytes.
	# n_req_files = 0
	if requirements != None:
		argument += ' Requirements:'
		for requirement in requirements:
			argument += ' '
			argument += requirement
			# n_req_files += 1
	
	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sd.connect( server_port_tuple )
	
	# INFORMS SERVER THE STRUCT
	header = struct.pack('i i', 0, len(argument))
	sd.send( header )
	
	# SENDS SERVER THE COMMAND/ACTION TO BE EXECUTED
	sd.send(bytes(argument, "utf-8"))

	# SEND FILES TO SERVER
	if requirements != None:
		for requirement in requirements:
			print(f'{BLU}> sending', requirement, RST)
			if '.o' in requirement: 
				file = open(file_path(requirement), 'rb')
				
			else:
				file = open(file_path(requirement), 'r')
			
			file_to_send = file.read()

			if '.o' in requirement:
				sd.send( file_to_send )
			else:
				sd.send(bytes(file_to_send, "utf-8"))
			
			file.close()

			file_confirmation = sd.recv(1024)
			file_confirmation = file_confirmation.decode("utf-8")
			print('Should be receiving a file confirmation. Nothing else.')
			print(CYN)
			print(f"{CYN} {file_confirmation} {RST}")

	return sd
	

def get_cheapest_host(hosts, argument, requirements=None):
	'''
	Simultaneously get the cost of each remote host, 
	and report back the remote host with the lowest cost
	'''
	n_req_files = 0
	if requirements != None:
		argument += ' Requirements: '
		for requirement in requirements:
			argument += requirement
			argument += ' '
			n_req_files += 1
	
	frame = struct.pack('i i', 1, len(argument))

	cheapest_host = 0
	lowest_cost = float('inf')

	for i in range(len(hosts)):
		sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sd.connect( hosts[i] )

		sd.send( frame )

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
					requirements = action[1].strip('requires').split()

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
					reply = sd.recv(8)
					
					# DECRYPT HEADER
					header = struct.unpack('i i', reply)
					exit_status = header[0]
					output_size = header[1]
					print(f"< out_size:\n{output_size}")
					print(f"< status:\n{exit_status}")

					reply = sd.recv(output_size)
					output = reply.decode("utf-8")
					print(f"< output:\n{output}")
					
					if exit_status != 0:
						error_in_actionset = True
					
					sd.close()
					inputs.remove(sd)
					
					outputs_received += 1
					if outputs_received >= total_actions:
						still_waiting_for_outputs = False
				
				# READ FROM SERVER, WHILST CONNECTED
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

# NOTE: SHOULD WORK WITH `python3 client-p.py`

# for action in rake_dict[ actionset ]:
			
# 	# * IF ACTION IS REMOTE, THEN CHECK COST FROM EACH SERVER
# 	if action[0].find('remote-') == 0:

# 		cheapest_host = get_cheapest_host( hosts ) # cost simulateonusly

# 		# EXECUTE ON CHEAPEST REMOTE HOST
# 		print(f"{YEL} --- REMOTE EXECUTION --- {RST}")
# 		print(f"executing order on {cheapest_host}")
# 		execute_on_server( cheapest_host , action[0].split("remote-")[1])


# for actionset in actionset_names:
	# processes = []
	# if error_in_actionset:
	# 	print("error detected in actionset - halting subsequent actionsets")
	# 	break

	# for action in rake_dict[ actionset ]:
	# 	pid = os.fork()
	# 	# CHILD PROCESS
	# 	if pid == 0:
	# 		#* IF ACTION IS REMOTE, THEN CHECK COST FROM EACH SERVER
	# 		if action[0].find('remote-') == 0:
	# 			argument = action[0].split("remote-")[1]
	# 			requirements = None
	# 			# HAS REQUIREMENT FILES
	# 			if len(action) > 1:
	# 				requirements = action[1].strip('requires').split()

	# 			cheapest_host = get_cheapest_host( hosts , argument ) # cost simulateonusly

	# 			# EXECUTE ON CHEAPEST REMOTE HOST
	# 			print(f"{YEL} --- REMOTE EXECUTION --- {RST}")
		
	# 			exit_status = execute_on_server( cheapest_host , argument , requirements )
	# 		#* ELSE, EXECUTE ON LOCAL SERVER
	# 		else:
		
	# 			requirements = None
	# 			# HAS REQUIREMENT FILES
	# 			if len(action) > 1:
	# 				requirements = action[1].strip('requires').split()

	# 			print(f"{YEL} --- LOCAL EXECUTION --- {RST}")
		
	# 			exit_status = execute_on_server( ('localhost' , DEFAULT_PORT) , action[0], requirements )
	
	# 		sys.exit(exit_status)
	# 	# PARENT PROCESS
	# 	else:
	# 		processes.append(pid)

	# # WAIT TILL ALL ACTIONS HAVE BEEN EXECUTED
	# while processes:
	# 	pid, exit_code = os.waitpid(-1, 0)
	# 	if pid != 0:
	# 		if pid in processes:
	# 			processes.remove(pid)
	# 			if (exit_code >> 8) != 0:
	# 				error_in_actionset = True
