import os

# Function that receives a filename and then returns a list of lines in that file.
def fread(filename):
	rfile = open(filename, 'r')
	
	lines = rfile.readlines()
	
	rfile.close()
	
	count = 0
	
	for line in lines:
		
		if line.find('#') >= 0:	# strip '#' and all characters after it from that line
		
			split_string = line.split('#', 1)
			lines[count] = split_string[0]
		
		lines[count] = lines[count].rstrip('\n')	# strip newline
		count += 1
	return lines

# Function that converts all items in a list to a dictionary, which is then returned.	
def dict_process(items):
	
	# Dictionary holding the port number, a 1D array of hosts and a 2D array of action sets.
	item_dictionary = {'Port': '', 'Hosts': []}
	
	# variables for the action set
	count = 1
	action = []
	
	for item in items:
		if item.find('PORT') >= 0:
			item_dictionary['Port'] = item.split('= ', 1)[1]
		
		if item.find('HOST') >= 0:
			item = item.replace('HOSTS = ', '')
			item_dictionary['Hosts'] = item.split(' ', item.count(' '))
			
		if item.find('actionset' + str(count) + ':') >= 0:
			item_dictionary['Action Set ' + str(count)] = []
			count += 1
		
		if item.count('\t') == 1:
			if len(action) == 1:
				item_dictionary['Action Set ' + str(count - 1)].append(action)
				action = []
				action.append(item.strip())
			else:
				action.append(item.strip())
		
		if item.count('\t') == 2:
			action.append(item.strip())
			item_dictionary['Action Set ' + str(count - 1)].append(action)
			action = []
		
		
	
	count = 0
	for host in item_dictionary.get('Hosts'):
		if host.find(':') >= 0:
			item_dictionary['Hosts'][count] = host.split(':', 1)
		count += 1
			
	return item_dictionary

def main():
	arr = os.listdir()	# array of all files in the client folder.
	for item in arr:
		if not item == 'client-p.py' and not os.stat(item).st_size == 0:
			s_list = fread(item)
			rake_dict = dict_process(s_list)
			print('\n', 'This is what was in the file\n', s_list)
			print('\n', 'This is a dictionary of the port, hosts and action sets\n',rake_dict)
	
main()

# NOTE: SHOULD WORK WITH `python3 client-p.py`
