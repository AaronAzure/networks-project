# CITS3003 2022 Project, written by:
# Aaron Wee		(22702446)
# Daniel Ling		(22896002)
# Muhammad Maaz Ahmed	(22436686)

import os, getopt
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

############HARDCODE, GET RID OF THIS LATER##################################
addr = '192.168.43.147'	# Server address.
port_num = 1234
server_addr = (addr, port_num)

HOST = 'localhost'
PORT_NUM = 12345
SERVER_ADDR = (HOST, PORT_NUM)
VERBOSE = False
rakefile  = 'Rakefile'	# Will be used to store rakefile.
#################################################################################

# Function that receives a filename and then returns a list of lines in that file.
def fread(filename):
	rfile = open(filename, 'r')
	lines = rfile.readlines()
	rfile.close()
	
	count = 0
	for line in lines:
		
		# strip '#' and all characters after it from that line
		if line.count('#') > 0:	
			lines[count] = line.split('#', 1)[0]
		
		lines[count] = lines[count].rstrip('\n')	# strip newline
		count += 1
	return lines


# Function that converts all items in a list to a dictionary, which is then returned.	
def dict_process(items):
	
	# Dictionary holding the port number, a 1D array of hosts and a 2D arrays of action sets.
	item_dictionary = {'Port': '', 'Hosts': []}
	
	# variables for the action set
	count = 1
	action = []
	current_actionset = ''
	
	for item in items:
		# LINE STARTS WITH PORT, SO GET AND STORE DEFAULT PORT NUMBER.
		if item.find('PORT') >= 0:
			item_dictionary['Port'] = int(item.split('= ', 1)[1])
		
		# LINE STARTS WITH HOSTS, SO GET AND STORE HOST(S).
		elif item.find('HOSTS') >= 0:
			item = item.replace('HOSTS = ', '')
			item_dictionary['Hosts'] = item.split(' ', item.count(' '))
			
		# LINE STARTS WITH actionset, GET AND STORE Action.
		elif item.find('actionset' + str(count) + ':') >= 0:
			item_dictionary['Action Set ' + str(count)] = []
			current_actionset = 'Action Set ' + str(count)
			count += 1
		
		elif item.count('\t') == 1 and not item == '\t':
			item_dictionary[current_actionset].append([item.strip()])
		
		elif item.count('\t') == 2 and len(item_dictionary[current_actionset]) > 0:
			item_dictionary[current_actionset][-1].append(item.strip())
		
		
	# All hosts with no specified port number get assigned the default port number.
	count = 0
	for host in item_dictionary.get('Hosts'):
		if host.find(':') >= 0:
			item_dictionary['Hosts'][count] = (host.split(':', 1)[0], int(host.split(':', 1)[1]))
		elif host is '':
			item_dictionary['Hosts'].remove(host)
		else:
			item_dictionary['Hosts'][count] = (host, item_dictionary['Port'])
		count += 1

		
			
	return item_dictionary


# Function that receives a dictionary and executes all actionsets within it.
def execute_action_sets(rdictionary):
	actionsets = []		# List holding all the action sets.
	action_failure = False		# If True, then do not execute the next actionset.
	
	for key in rdictionary:
		if key.find('Action Set ') >= 0:
			actionsets.append(key)
	
	for actionset in actionsets:			# Moving through the actionset.
		for action in rdictionary[actionset]:	# Moving through the actions in the actionset.
			
			# External programs that do not depend on other file(s).
			if len(action) == 1:
				arguments = action[0].split()
				
				# Non-remote action.
				if arguments[0].find('remote') < 0:
					
					try:	# Catch actions that subprocess.run() cannot handle.
						action_failure = external_program_results(arguments, action_failure)
					except:
						print('Subprocess cannot process non command-line actions.\n')
						action_failure = True
						
				# Remote action.
				else:
					remote_argument = ' '.join(arguments)
					remote_argument = remote_argument.split('-')[1]
					
					remote_function(remote_argument, rdictionary['Hosts'])
				
			
			# External programs that do depend on other file(s).
			if len(action) == 2:
				arguments = action[0].split()
				action[1] = action[1].lstrip('requires')
				required = action[1].split()
				
				if VERBOSE == True: print("DEBUG: REQUIRED:", required) # DEBUGGING
				
				count = 0
				
				# Non-remote action.
				if arguments[0].find('remote') < 0: 	# Non-remote compiling.
					for argument in arguments:	# Find the path of required files.
						path = None
						
						if argument in required:
							path = file_path(argument)
						
						if not path == None:
							arguments[count] = path
						
						count += 1
						
					
					try:	# Catch actions that subprocess.run() cannot handle.
						action_failure = external_program_results(arguments, action_failure)
					except:
						print('Subprocess cannot process non command-line actions.\n')
						action_failure = True
							 
				# Remote action.	
				else:
					remote_argument = ' '.join(arguments)
					remote_argument = remote_argument.split('-')[1]
					
					remote_function(remote_argument, rdictionary['Hosts'], required)	
		
		if action_failure:	# An action(s) failed. Stop executing actionsets.
			print('Action failure notification', '\n')
			return actionsets		
	
	return actionsets

# Function to find a file path in the working directory.
def file_path(filename):
	for r, d, f in os.walk(os.getcwd()):
		if filename in f:
			return os.path.join(r, filename)
	return None
	
# Print results of the external program. Also returns action execution failure if that occurs.
def external_program_results(arguments, execution_failure):
	output = subprocess.run(arguments, capture_output = True)
	
	# Printing the output of the execution in a readable format.
	print('Arguments:', ' '.join(output.args))		# Input arguments.
	print('Exit status:', output.returncode)		# Success/failure report.
				
	if not output.stdout.decode() == '':			# Prints output if they exist.
		print('Output:', output.stdout.decode())
		
	if not output.stderr.decode() == '':			# Prints error and sets failure flag.
		print('Error:', output.stderr.decode())
		execution_failure = True
	
	print('')						# Just for formatting.
	
	return execution_failure
	
# Function that performes actions that require the server. 
# Receives the action and a list of the necessary files.
def remote_function(argument, hostlist, requirements = None):
	# If there are file requirements, add them as a string to arguments, seperated by ' Requirements: '.
	if not requirements == None:
		argument += ' Requirements: '
		for requirement in requirements:
			argument += requirement
			argument += ' '
	
	print("Going to send this to server:", argument)
	
	print(hostlist)
		
	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sd.connect(SERVER_ADDR)
	sd.send(bytes(argument, "utf-8"))
		
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
	
	
	#print('Arguments:', ' '.join(status.args))
	
####################################################################################################


def main():
	global HOST
	global PORT_NUM
	global VERBOSE
	global rakefile

	# OPTION FLAGS
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
		
	directory = os.getcwd()	# The working directory.
	
	if len(sys.argv) == 2:
		rakefile = sys.argv[1]
	
	print('\n', 'Looking at this file:', rakefile)
		
	string_list = fread(rakefile)
	###DEBUG###
	print('\nThis is what was in the file:\n', string_list, '\n')
	###DEBUG###

	rake_dict = dict_process(string_list)
	###DEBUG###
	print('\nDictionary:','\n', rake_dict, '\n')
	###DEBUG###
	
	actionsets = []	# List holding all the action sets.
			
	a_sets = execute_action_sets(rake_dict)
			
main()

# NOTE: SHOULD WORK WITH `python3 client-p.py`
