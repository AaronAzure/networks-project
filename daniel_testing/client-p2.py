# CITS3003 2022 Project, written by:
# Aaron Wee				(22702446)
# Daniel Ling			(22896002)
# Muhammad Maaz Ahmed	(22436686)

import os
import subprocess
import sys
import socket

BOLD = "\033[1;30m"
RED = "\033[1;31m"
GRN = "\033[1;32m"
YEL = "\033[1;33m"
MAG = "\033[1;35m"
CYN = "\033[1;36m"
RST = "\033[0m"


port_num = 12345

# Function that receives a filename, 
# and then returns a list of lines of useful information from the specified file
def fread(filename):
	rfile = open(filename, 'r')
	lines = rfile.readlines()
	rfile.close()
	
	count = 0
	result = []
	
	for line in lines:

		# skip empty lines
		if line == '\n':
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


# Function that converts all items in a list to a dictionary, which is then returned.	
def parse_file(items):
	print(items)
	# Dictionary holding the port number, a 1D array of hosts and a 2D arrays of action sets.
	item_dictionary = {'Port': 0, 'Hosts': []}
	
	# variables for the action set
	count = 0
	action = []
	current_actionset_name = ""
	
	for item in items:
		# IF LINE STARTS WITH PORT, GET AND STORE DEFAULT PORT NUMBER
		if item.find('PORT') == 0:
			item_dictionary['Port'] = int(item.split()[-1])

		# IF LINE STARTS WITH HOSTS, GET AND STORE HOST(S)
		elif item.find('HOST') == 0:
			item = item.replace('HOSTS = ', '')
			item_dictionary['Hosts'] = item.split(' ', item.count(' '))

		# IF LINE STARTS WITH actionset, GET AND STORE Action	
		elif item.find('actionset') == 0:
			current_actionset_name = item.split(':')[0]
			item_dictionary[ current_actionset_name ] = []
			count += 1
		
		# Note to self: Do
		elif item.count('\t') == 1:
			item_dictionary[ current_actionset_name ].append( [item.strip()] )
		
		elif item.count('\t') == 2 and len(item_dictionary[ current_actionset_name ]) > 0:
			item_dictionary[ current_actionset_name ][-1].append(item.strip())
		
		
	# All hosts with no specified port number get assigned the default port number.
	count = 0
	for host in item_dictionary.get('Hosts'):
		if host.find(':') >= 0:
			item_dictionary['Hosts'][count] = [host.split(':', 1)[0], int(host.split(':', 1)[1])]
		else:
			item_dictionary['Hosts'][count] = [host, item_dictionary['Port']]
		count += 1
			
	return item_dictionary


# Function that receives a dictionary and executes all actionsets within it.
def execute_action_sets(rdictionary):
	actionsets = []	# List holding all the action sets.
	
	for key in rdictionary:
		if key.find('actionset') == 0:
			actionsets.append(key)
	
	for actionset in actionsets:
		for action in rdictionary[actionset]:
			
			# External programs that do not depend on files.
			if len(action) == 1:
				arguments = action[0].split()
				
				if arguments[0].find('remote-') < 0: # Non-remote compiling.
					print("Looking at", arguments)
					if subprocess.run(arguments) == 0:
						return
					else:
						print(subprocess.run(arguments, capture_output = True), '\n')
						
				if arguments[0].find('remote-') >= 0: # Remote compiling.
					print(remote_function(arguments))
				
			
			# External programs that do depend on files.
			if len(action) == 2:
				arguments = action[0].split()
				action[1] = action[1].lstrip('requires ')
				required = action[1].split()
				
				count = 0
				
				if arguments[0].find('remote') < 0: # Non-remote compiling.
					for argument in arguments:
						path = None
						
						if argument.find('.') >= 0:
							path = file_path(argument)
						
						if not path == None:
							arguments[count] = path
						
						count += 1
						
					
					if not subprocess.call(arguments) == 0:
						print('\n')
						return
					else:
						output = subprocess.run(arguments, capture_output = True)
						print(output, '\n')
					
				else: # Remote compiling
					print('dab')	# Re					
	
	return actionsets

# Function to find a file path in the working directory.
def file_path(filename):
	for r, d, f in os.walk(os.getcwd()):
		if filename in f:
			return os.path.join(r, filename)
	return None

# Function that performes actions that require the server. 
# Receives the action and a list of the necessary files.
def write_file_to_server(sd, message):
    # print(f"{GRN} --> {message} {RST}"))
	message = message.split("remote-")[1]
	sd.send(bytes(message, "utf-8"))
	# sd.send(bytes(message, "utf-8"))
    # if write(sd, message, strlen(message)) < 0:
    #     return -1
        
    # SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
	reply = sd.recv(2048)
	if reply:
		reply = reply.decode("utf-8")
		print(CYN) 
		print(f"{CYN} <-- {reply} {RST}") 
    
    # SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
	status = sd.recv(2048)
	if status:
		status = status.decode("utf-8")
		print(CYN) 
		print(f"{CYN} <-- {status} {RST}") 

    # return status




####################################################################################################


def main():

	directory = os.getcwd()	# The working directory.
	rakefile  = 'Rakefile'	# Will be used to store rakefile.
	
	if len(sys.argv) == 2:
		rakefile = sys.argv[1]
	
	# print('\n', 'Looking at this file: ', rakefile)
		
	string_list = fread(rakefile)
	# print('\n', 'This is what was in the file\n', string_list)

	action_table = parse_file(string_list)
	print(action_table)

	actionsets_keys = []	# List holding all the action sets.
	
	for key in action_table:
		if key.find('actionset') == 0:
			actionsets_keys.append(key)
			

	# hostname = socket.gethostname()
	# print(hostname)

	# sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sd.connect(('10.10.255.255', 12345))
	# sd.connect(('ASUS', 12345))

	for actionsets_key in actionsets_keys:
		for action in action_table[ actionsets_key ]:
            # EXECUTE ACTION ON SERVER
			if action[0].find('remote-') == 0:
				write_file_to_server(sd, action[0])
            # EXECUTE ACTION ON LOCAL MACHINE
			else:
				os.system(action[0])

	
	# server_addr = ('localhost', port_num)
	# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock_desc:
	# 	sock_desc.connect(server_addr)
	# 	for actionset in actionsets:
	# 		for action in action_table[actionset]:
	# 			# sock_desc.send(bytes("Hello, world", "utf-8"))
	# 			sock_desc.send(bytes(action[0], "utf-8"))
	# 			data = sock_desc.recv(2048)
	# 			if data:
	# 				print(data.decode("utf-8"))
			
	# print('\n', 'This is a dictionary of the port, hosts and action sets\n', action_table)
			
	# a_sets = execute_action_sets(action_table)
			
main()

# NOTE: SHOULD WORK WITH `python3 client-p.py`
