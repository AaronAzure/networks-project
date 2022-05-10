# CITS3003 2022 Project, written by:
# Aaron Wee				(22702446)
# Daniel Ling			(22896002)
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


HOST = 'localhost'
PORT_NUM = 12345
VERBOSE = False
rakefile  = 'Rakefile'	# Will be used to store rakefile.

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
	# print(items)
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
				HOST = int(arg)
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

	
	# print('\n', 'Looking at this file: ', rakefile)
		
	string_list = fread(rakefile)
	# print('\n', 'This is what was in the file\n', string_list)

	action_table = parse_file(string_list)
	# print(action_table)

	actionsets_keys = []	# List holding all the action sets.
	
	for key in action_table:
		if key.find('actionset') == 0:
			actionsets_keys.append(key)
			

	sd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sd.connect((HOST, PORT_NUM))

	for actionsets_key in actionsets_keys:
		for action in action_table[ actionsets_key ]:
            # EXECUTE ACTION ON SERVER
			if action[0].find('remote-') == 0:
				write_file_to_server(sd, action[0])
            # EXECUTE ACTION ON LOCAL MACHINE
			else:
				os.system(action[0])
			
			

if __name__ == "__main__":
    main()

# NOTE: SHOULD WORK WITH `python3 rake-p.py`
