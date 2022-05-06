# CITS3003 2022 Project, written by:
# Aaron Wee		(22702446)
# Daniel Ling		(22896002)
# Muhammad Maaz Ahmed	(22436686)

import os
import subprocess
import sys
import socket

# Function that receives a filename and then returns a list of lines in that file.
def fread(filename):
	rfile = open(filename, 'r')
	lines = rfile.readlines()
	rfile.close()
	
	count = 0
	for line in lines:
		
		# strip '#' and all characters after it from that line
		if line.find('#') >= 0:	
			split_string = line.split('#', 1)
			lines[count] = split_string[0]
		
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
	
	for item in items:
		if item.find('PORT') >= 0:
			item_dictionary['Port'] = int(item.split('= ', 1)[1])
		
		if item.find('HOST') >= 0:
			item = item.replace('HOSTS = ', '')
			item_dictionary['Hosts'] = item.split(' ', item.count(' '))
			
		if+ item.find('actionset' + str(count) + ':') >= 0:
			item_dictionary['Action Set ' + str(count)] = []
			count += 1
		
		#Note to self: Do
		if item.count('\t') == 1:
			if len(action) == 1:
				item_dictionary['Action Set ' + str(count - 1)].append(action)
				action = []
				action.append(item.strip())
			else:
				action.append(item.strip())
		
		if item.count('\t') == 2:
			# req_files = item.split('requires ',1)[1].split(' ')
			# action.append(req_files)
			action.append(item.strip())
			item_dictionary['Action Set ' + str(count - 1)].append(action)
			action = []
		
		
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
		if key.find('Action Set ') >= 0:
			actionsets.append(key)
			
	print('\n', 'This is the action sets about to be executed\n', actionsets, '\n')
	
	for actionset in actionsets:
		for action in rdictionary[actionset]:
			
			# External programs that do not depend on files.
			if len(action) == 1:
				os.system(action[0])
			
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
				output = subprocess.run(arguments, capture_output = True)
				print(output)
				print('\n')
				
				if not subprocess.call(arguments) == 0:
					print('\n')
					return
	
	return actionsets

# Function to find a file path in the working directory.
def file_path(filename):
	for r, d, f in os.walk(os.getcwd()):
		if filename in f:
			return os.path.join(r, filename)
	return None


####################################################################################################


def main():
	server_addr = ('localhost', 12345)
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	try:
		s.connect(server_addr)
		print("Connected to {:s}".format(repr(server_addr)))

		# for i in range(5):
		# 	print("")
		# 	# payload_out = Payload(1, i, random.uniform(-10, 30))
		# 	print("Sending id={:d}, counter={:d}, temp={:f}".format(payload_out.id,
		# 														payload_out.counter,
		# 														payload_out.temp))
		# 	# nsent = s.send(payload_out)
		# 	# Alternative: s.sendall(...): coontinues to send data until either
		# 	# all data has been sent or an error occurs. No return value.
		# 	print("Sent {:d} bytes".format(nsent))

		# 	# buff = s.recv(sizeof(Payload))
		# 	# payload_in = Payload.from_buffer_copy(buff)
		# 	print("Received id={:d}, counter={:d}, temp={:f}".format(payload_in.id,
		# 														payload_in.counter,
		# 														payload_in.temp))
	except AttributeError as ae:
		print("Error creating the socket: {}".format(ae))
	except socket.error as se:
		print("Exception on socket: {}".format(se))
	finally:
		print("Closing socket")
		s.close()

	directory = os.getcwd()	# The working directory.
	rakefile  = 'Rakefile'	# Will be used to store rakefile.
	
	if len(sys.argv) == 2:
		rakefile = sys.argv[1]
	
	print('\n', 'Looking at this file: ', rakefile)
		
	string_list = fread(rakefile)
	print('\n', 'This is what was in the file\n', string_list)
			
	rake_dict = dict_process(string_list)
	print('\n', 'This is a dictionary of the port, hosts and action sets\n',rake_dict)
			
	a_sets = execute_action_sets(rake_dict)
			
main()

# NOTE: SHOULD WORK WITH `python3 client-p.py`
