# CITS3003 2022 Project, written by:
# Aaron Wee		(22702446)
# Daniel Ling		(22896002)
# Muhammad Maaz Ahmed	(22436686)

import os, getopt
import subprocess
import sys
import socket
import time #! DELETE

BOLD = "\033[1;30m"
RED = "\033[1;31m"
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
protocol = ''
#################################################################################

def fread(filename):
	'''
	Function that receives a filename and then returns an important and stripped list of lines.
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
	Extract important information from @param items into a dictionary format
	Function that converts all items in a list to a dictionary, which is then returned.	
	'''
	
	# Dictionary holding the port number, a 1D array of hosts and a 2D arrays of action sets.
	item_dictionary = {'Port': '', 'Hosts': []}
	
	# variables for the action set
	count = 1
	action = []
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
			item_dictionary[current_actionset].append([item.strip()])
		
		# STORE REQUIREMENTS FOR PREVIOUS ACTION.
		elif item.count('\t') == 2 and len(item_dictionary[current_actionset]) > 0:
			item_dictionary[current_actionset][-1].append(item.strip())
		
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


def execute_action_sets(rdictionary):
	'''
	Function that receives a dictionary and executes all actionsets within it.
	'''
	actionsets = []		# List holding all the action sets.
	action_failure = False		# If True, then do not execute the next actionset.
	
	for key in rdictionary:
		if key.find('Action Set ') >= 0:
			actionsets.append(key)
	
	global HOST
	global DEFAULT_PORT
	for actionset in actionsets:			# Moving through the actionset.
		for action in rdictionary[actionset]:	# Moving through the actions in the actionset.
			
			# External programs that do not depend on other file(s).
			if len(action) == 1:
				arguments = action[0].split()
				
				# Non-remote action.
				if arguments[0].find('remote') < 0:
					print(f"{YEL} --- LOCAL EXECUTION --- {RST}")
					remote_argument = ' '.join(arguments)
					
					execute_on_server('localhost', DEFAULT_PORT, remote_argument)
						
				# Remote action.
				else:
					print(f"{YEL} --- REMOTE EXECUTION --- {RST}")
					remote_argument = ' '.join(arguments)
					remote_argument = remote_argument.split('-')[1]
					
					execute_on_server(HOST, DEFAULT_PORT, remote_argument)
				
			
			# External programs that do depend on other file(s).
			if len(action) == 2:
				arguments = action[0].split()
				action[1] = action[1].lstrip('requires')
				required = action[1].split()
				
				if VERBOSE == True: 
					print("DEBUG: REQUIRED:", required) # DEBUGGING
				
				count = 0
				
				# Non-remote action.
				if arguments[0].find('remote') < 0: 	# Non-remote compiling.
					print(f"{YEL} --- LOCAL EXECUTION --- {RST}")
					remote_argument = ' '.join(arguments)
					
					execute_on_server('localhost', DEFAULT_PORT, remote_argument, required)
							
				# Remote action.	
				else:
					print(f"{YEL} --- REMOTE EXECUTION --- {RST}")
					remote_argument = ' '.join(arguments)
					remote_argument = remote_argument.split('-')[1]
					
					execute_on_server(HOST, DEFAULT_PORT, remote_argument, required)	
		
		if action_failure:	# An action(s) failed. Stop executing actionsets.
			print('Action failure notification', '\n')
			return actionsets		
	
	return actionsets


def file_path(filename):
	'''
	Function to find a file path in the working directory.
	'''
	for r, d, f in os.walk(os.getcwd()):
		if filename in f:
			return os.path.join(r, filename)
	return None	

def execute_on_server(server_port_tuple, argument, requirements = None):
	'''
	Function that performes actions that require the server. 
	Receives the action and a list of the necessary files.
	'''

	# If there are file requirements, add them as a string to arguments, seperated by ' Requirements: '.
	# Additionally, these files will need to be sent to the server as well. Meaning the server
	# must also know the size of the file in the case it exceeds 1024 bytes.
	if not requirements == None:
		argument += ' Requirements: '
		for requirement in requirements:
			argument += requirement + '=' + str(os.path.getsize(file_path(requirement)))
			argument += ' '

	protocol = '01000 | ' + str(len(argument)) + ' | ' + argument
	print("Protocol sending server an argument (possibly with requirements):", protocol)
	
	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sd.connect( server_port_tuple )
	# sd.connect((server, port))
	sd.send(bytes(argument, "utf-8"))	# SENDING MESSAGE
			
		
	# SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
	reply = sd.recv(1024)
	#time.sleep(1)	#! DELETE
	if reply:
		reply = reply.decode("utf-8")
		print(CYN)
		print(f"{CYN} {reply} {RST}")

	# SEND FILES TO SERVER, WHICH INFORMS CLIENT IF THE FILES WERE RECEIVED.
	if not requirements == None:
		for requirement in requirements:
			print('sending', requirement)
			if '.o' in requirement: 
				file = open(file_path(requirement), 'rb')
				
			else:
				file = open(file_path(requirement), 'r')
			
			reading_file = file.read()

			if '.o' in requirement:
				sd.send(reading_file)
			else:
				sd.send(bytes(reading_file, "utf-8"))
			
			file.close()

			file_confirmation = sd.recv(1024)
			file_confirmation = file_confirmation.decode("utf-8")
			print('Should be receiving a file confirmation. Nothing else.')
			print(CYN)
			print(f"{CYN} {file_confirmation} {RST}")
			
	# SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
	print('Should be receiving an exit output.')
	status = sd.recv(1024)
	#time.sleep(1)	#! DELETE
	if status:
		status = status.decode("utf-8")
		print(CYN) 
		print(f"{CYN} {status} {RST}")
	
	if not requirements == None:
		output_message = sd.recv(1024).decode("utf-8")
		if output_message:
			output_message = output_message.split('=')
			print(CYN)
			print(f"{CYN} {'Will receive file'} {output_message[0]} {'of size'} {output_message[1]} {'from the server.'}")
		
		output_file = sd.recv(int(output_message[1]))
		file = open(output_message[0], 'wb')
		file.write(output_file)
		file.close()
		
	sd.close()
	
	#print('Arguments:', ' '.join(status.args))
	

def read_option_flags():
	global HOST
	global VERBOSE
	global PORT_NUM
	global SOCKET_NUM

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


def get_cost_from_server(server_port_tuple):
	'''
	Function that asks server for the cost of executing an action.
	Returns -1 if server not found, else return the cost.
	'''
	protocol = '10000 | 0 |'
	print('Protocol asking server for cost of executing action', protocol)

	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	print(server_port_tuple)
	sd.connect( server_port_tuple )
	sd.send(bytes(protocol, "utf-8"))

	reply = sd.recv(1024)
	
	if reply:
		reply_cost = reply.decode("utf-8")
		reply_cost = reply_cost.split('|')[2]
		return int(reply_cost)
	return -1

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
	###DEBUG###

	rake_dict = extract_info(string_list)
	###DEBUG###
	if VERBOSE:
		print('\nDictionary:','\n', rake_dict, '\n')
	###DEBUG###
	
	hosts = rake_dict['Hosts']
	actionset_names = get_action_set_names(rake_dict)

	if VERBOSE:
		print(f"hosts = {hosts}")
		print(f"actionset_names = {actionset_names}")
	
	for actionset in actionset_names:
		for action in rake_dict[ actionset ]:
			# * IF ACTION IS REMOTE, THEN CHECK COST FROM EACH SERVER
			if action[0].find('remote-') == 0:
				cheapest_host = 0
				lowest_cost = 1000

				for i in range(len(hosts)):
					cost = get_cost_from_server(hosts[i])
					
					# REMEMBER THE REMOTE HOST RETURNING THE LOWEST COST TO RUN THE COMMAND
					if cost < lowest_cost:
						lowest_cost = cost
						cheapest_host = i

				# EXECUTE ON CHEAPEST REMOTE HOST
				print(f"{YEL} --- REMOTE EXECUTION --- {RST}")
				print(f"executing order on {hosts[cheapest_host]}")

				if len(action) == 1:
					execute_on_server( hosts[cheapest_host] , action[0].split("remote-")[1])
				else:
					execute_on_server( hosts[cheapest_host] , action[0].split("remote-")[1], action[1].strip('requires').split())

				
			# * ELSE, EXECUTE ON LOCAL SERVER
			else:
				print(f"{YEL} --- LOCAL EXECUTION --- {RST}")
				if len(action) == 1:
					execute_on_server( ('localhost' , DEFAULT_PORT) , action[0])
				else:
					execute_on_server( ('localhost', DEFAULT_PORT), action[0], action[1].strip('requires').split())

			# * IF ACTION HAS REQUIREMENT FILE(S)
			# if len(action) > 1:
			# GET COST FOR ACTION FROM EACH HOST (SERVER)
			# if 
		


if __name__ == "__main__":
	main()

# NOTE: SHOULD WORK WITH `python3 client-p.py`
