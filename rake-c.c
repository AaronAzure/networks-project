// CITS3003 2022 Project, written by:
// Muhammad Maaz Ahmed	(22436686)
// Aaron Wee				(22702446)
// Daniel Ling			(22896002)

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h> 
#include <sys/wait.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/select.h>

#include <string.h>
#include <dirent.h>
#include <stdbool.h>
#include <netdb.h>
#include <arpa/inet.h>	//inet_addr
#include <getopt.h>
#include <time.h>

#define     MAX_FILES_IN_DIRECTORY		128
#define     MAX_FILES_TO_PROCESS		128
#define     MAX_HOSTS					32
#define     MAX_ACTIONS					32
#define     MAX_ACTIONSETS				32
#define     MAX_REQUIREMENTS			32
#define     BUFFER_SIZE					2048
#define     MAX_FILE_NAME				64
#define     MAX_LINE_LENGTH				2048

#define     RED							"\033[0;31m"
#define     GRN							"\033[0;32m"
#define     YEL							"\033[0;33m"
#define     BLU							"\033[0;34m"
#define     MAG							"\033[0;35m"
#define     CYN							"\033[0;36m"
#define     WHT							"\033[0;37m"
#define     RST							"\033[0m"


// -------------------------------------------------------------------
// ----------------------- GLOBAL VARIABLES --------------------------


typedef struct Action
{
    char    action[BUFFER_SIZE];
    bool    isRemote;
    
    int     nRequiredFiles;
    char    requiredFiles[MAX_REQUIREMENTS][BUFFER_SIZE];
} Action;


typedef struct ActionSet
{
    char    actionSetName[BUFFER_SIZE];
    
    int     nActions;
    Action  actions[MAX_ACTIONS];
} ActionSet;


typedef struct Host
{
    int     port;
    char    host[MAX_FILE_NAME];
} Host;


typedef struct Rackfile
{
    char        filename[MAX_FILE_NAME];

    int         nHosts;
    Host        hosts[MAX_HOSTS];

    int         nActionSets;
    ActionSet   actionSets[MAX_ACTIONSETS];    //! ERROR
} Rackfile;


char    rackfile_name[MAX_FILE_NAME];
char    host[16];
int     port_num = 12345;
int     default_port;
int     verbose = false;

Rackfile rackfile;

typedef struct HeaderToServer
{
    int	asking_for_cost;
    int	message_length;	// COMMAND OR REQUIRED FILENAME LENGTH
    int	n_required_files;
} HeaderToServer;

typedef struct HeaderFromServer
{
    int	exit_status;				// EXIT STATUS OF RUNNING COMMAND/ACTION
    int	output_len;					// FILENAME LENGTH OF CREATED/MODIFIED FILE
    int	output_filesize;			// LENGTH OF OUTPUT (STDOUT) OR CREATED/MODIFIED FILE SIZE
    int	output_filename_len;		// FILENAME LENGTH OF CREATED/MODIFIED FILE
    int	error_len;					// LENGTH OF OUTPUT (STDERR)
} HeaderFromServer;


// -------------------------------------------------------------------
// ---------------------------- METHODS ------------------------------

/**
 * @brief Remove leading whitespace characters from string
 * 
 * @param str - string to remove leading whitespace characters
 */
void trim_leading(char *str)
{
    int index, i;
    index = 0;

    // FIND LAST INDEX OF WHITESPACE CHARACTER 
    while (str[index] == ' ' || str[index] == '\t' || str[index] == '\n')
        index++;

    if (index != 0)
    {
        i = 0;
        while(str[i + index] != '\0')
        {
            str[i] = str[i + index];
            i++;
        }
        // MAKE SURE THAT STRING IS NULL TERMINATED
        str[i] = '\0'; 
    }
}

int count_leading_tabs(char *string)
{
    int index = 0;

    while (string[index] == '\t')
        index++;
    
    return index;
}


/**
 * @brief   Get the last word of string
 * 
 * @param string    string to be analysed
 * @return char*    last word of string
 */
char *get_last_word(char *string)
{
    const char *delimiter = " ";

    // Extract the first token
    char *token = strtok(string, delimiter);
    char *last_word = NULL;
    
    // loop through the string to extract all other tokens
    while( token != NULL ) 
    {
        last_word = token;
        token = strtok(NULL, delimiter);
    }

    return last_word;
}


/**
 * @brief   Find first occurrence of specified character in string
 * 
 * @param string    string to be analysed
 * @param substring character to be found
 * @return int      index of first occurrence of specified character
 */
int char_at(char *string, char substring)
{
    char *ptr = strchr(string, substring);
    if (ptr == NULL)
        return -1;
    return ((int) (ptr - string));
}


/**
 * @brief   Check if @param string starts with @param substring
 * 
 * @param string    
 * @param substring 
 * @return true 
 * @return false 
 */
bool starts_with(char *string, char *substring)
{
    return (strncmp(string, substring, strlen(substring)) == 0);
}


/**
 * @brief   (Debugging purposes) 
 *          For each anaylsed file:
 *           - Print port number
 *           - Print all host(s)
 *           - Print all actionset(s)
 * 
 */
void debug_rackfile()
{
    // HOST(S) + PORT NUMBER ( host:port )
    printf("hosts:\n");
    for (int h=0 ; h<rackfile.nHosts ; h++)
        printf(" - %s:%i\n", rackfile.hosts[h].host, rackfile.hosts[h].port);

    // ACTIONSETS
    for (int i=0 ; i<rackfile.nActionSets ; i++)
    {
        printf("%s:\n", rackfile.actionSets[i].actionSetName);
        for (int a=0 ; a<rackfile.actionSets[i].nActions ; a++)
        {
            printf(" - (%s)\t|%s|\n", rackfile.actionSets[i].actions[a].isRemote ? "true" : "false", rackfile.actionSets[i].actions[a].action);
            if (rackfile.actionSets[i].actions[a].nRequiredFiles > 0)
            {
                printf("  required files:\n");
                for (int r=0 ; r<rackfile.actionSets[i].actions[a].nRequiredFiles ; r++)
                    printf("   - %s\n", rackfile.actionSets[i].actions[a].requiredFiles[r]);
            }
        }
    }

    printf("\n\n");
}


/**
 * @brief   Analyse and process supposedly Rakefile(s) :
 *           - extract port number
 *           - extract host(s)
 *           - extract action set(s)
 *          
 * @param filename  file to analyse and process
 */
void parse_file(char *filename)
{

    if (verbose)
        printf("-- parsing %s\n\n", filename);

    FILE  *fp = fopen(filename, "r");
    char  line[BUFFER_SIZE];

    if (fp != NULL) 
    {
        strcpy(rackfile.filename, filename);
        int action_set_ind = 0;
        int action_ind    = 0;
        int *n_action_set = &rackfile.nActionSets;
        while (fgets(line, sizeof(line), fp) != NULL) 
        {
            // STORE NON-EMPTY LINES
            if (!starts_with(line, "\n")) // is a newline character
            {
                // TRIM UNTIL COMMENT SYMBOL
                char *ptr = strchr(line, '#');
                if (ptr != NULL) 
                    *ptr = '\0';

                // IF LINE STARTS WITH PORT, GET AND STORE DEFAULT PORT NUMBER
                if (starts_with(line, "PORT"))
                {
                    char *last_word = NULL;
                    last_word = get_last_word(line);
                    default_port = atoi(last_word);
                }
                // IF LINE STARTS WITH HOSTS, GET AND STORE HOST(S)
                else if (starts_with(line, "HOSTS"))
                {
                    int len = strlen("HOSTS = ");
                    char *substring = line;
                    substring += len;

                    const char *delimiter = " ";
                    char *token = strtok(substring, delimiter);
                    
                    // LOOP THROUGH THE STRING TO EXTRACT ALL OTHER TOKENS
                    int *nHosts = &rackfile.nHosts;
                    while ( token != NULL ) 
                    {
                        // HAS A SPECIFIED PORT NUMBER
                        char *separator = strchr(token, ':');
                        if (separator != NULL) 
                        {
                            *separator = '\0';
                            rackfile.hosts[*nHosts].port = atoi(separator + 1);
                            strcpy(rackfile.hosts[(*nHosts)++].host, token);
                        }
                        // NO SPECIFIED PORT NUMBER, SET DEFAULT PORT
                        else
                        {
                            rackfile.hosts[*nHosts].port = default_port;
                            strcpy(rackfile.hosts[(*nHosts)++].host, token);
                        }
                        token = strtok(NULL, delimiter);
                    }

                }
                // IF LINE STARTS WITH actionset, GET AND STORE Action
                else if (starts_with(line, "actionset"))
                {
                    // SAVE ACTION SET
                    if (action_set_ind + 1 == *n_action_set)
                    {
                        rackfile.actionSets[ action_set_ind ].nActions = action_ind;
                        action_set_ind++;
                    }
                    action_ind = 0;
                    (*n_action_set)++;
                    int end_of_action_set = char_at(line, ':');
                    strncpy(rackfile.actionSets[action_set_ind].actionSetName, line, end_of_action_set);
                }
                else 
                {
                    switch (count_leading_tabs(line))
                    {
                        case 1: // ACTION LINE

                            trim_leading(line);

                            if (line[strlen(line) - 1] == '\n')
                                line[strlen(line) - 1] = '\0';

							// EMPTY LINE ( ONLY HAD TABS)
							if (strcmp(line, "") == 0)
								continue;

                            if (starts_with(line, "remote-"))
                            {
                                rackfile.actionSets[ action_set_ind ].actions[action_ind].isRemote = true;
                                int len = strlen("remote-");
                                char *substring = line;
                                substring += len;
                                strcpy(rackfile.actionSets[ action_set_ind ].actions[action_ind++].action, substring);
                            }
                            else
                                strcpy(rackfile.actionSets[ action_set_ind ].actions[action_ind++].action, line);

                            break;

                        case 2: // REQUIREMENT LINE

                            // INVALID - NO PREVIOUS ACTION FOR REQUIREMENTS
                            if (action_ind == 0)
                                continue;
                            
                            action_ind--;	// PREVIOUS ACTION
                            trim_leading(line);
								
                            if (line[strlen(line) - 1] == '\n')
                                line[strlen(line) - 1] = '\0';

							// EMPTY LINE ( ONLY HAD TABS)
							if (strcmp(line, "") == 0)
								continue;

                            int len = strlen("requires");
                            char *substring = line;
                            substring += len;

                            const char *delimiter = " ";
                            char *token = strtok(substring, delimiter);
                            
                            // loop through the string to extract all other tokens
                            int *n_required_files = &rackfile.actionSets[ action_set_ind ].actions[action_ind].nRequiredFiles;
                            while ( token != NULL ) 
                            {
                                strcpy(rackfile.actionSets[ action_set_ind ].actions[action_ind].requiredFiles[(*n_required_files)++], token);
                                token = strtok(NULL, delimiter);
                            }
                            action_ind++;
                            break;

                        default:
                            break;
                    }
                }
            }
        }
        fclose(fp);
        rackfile.actionSets[ action_set_ind ].nActions = action_ind;
    }
    else
    {
		perror("fopen:");
    }
}


int establish_socket(char *host, int port)
{
	struct hostent     *hp = gethostbyname(host);
	
    if (hp == NULL) 
    {
        fprintf(stderr,"rlogin: unknown host\n");
        exit(2);
    }

	// CREATE SOCKET
    //  ASK OUR OS KERNEL TO ALLOCATE RESOURCES FOR A SOCKET
    int sd = socket(AF_INET, SOCK_STREAM, 0);
    if (sd < 0) 
    {
        perror("rlogin: socket");
        exit(3);
    }

    //  INITIALIZE FILEDS OF A STRUCTURE USED TO CONTACT SERVER
    struct sockaddr_in server;

    // memset(&server, 0, sizeof(server));
    memcpy(&server.sin_addr, hp->h_addr, hp->h_length);
    server.sin_family  = hp->h_addrtype;
	server.sin_port = htons( port );

    //  CONNECT TO SERVER
    if (connect(sd, (struct sockaddr *)&server, sizeof(server)) < 0) 
    {
        perror("rlogin: connect");
        exit(4);
    }

	return sd;
}


// '''
// Function that performes actions that require the server. 
// Receives the action and a list of the necessary files.
// '''
/**
 * @brief 	Performs an action on a remote specified server.
 * 
 * @param sd 		the socket descriptor connected to a server
 * @param action 	the action to be remotely executed
 */
void send_command_to_server(int sd, Action action)
{
	// INFORMS SERVER REGARDING THE PAYLOAD SIZE
	HeaderToServer header;
	
	header.asking_for_cost 	= 0;
	header.message_length 	= strlen(action.action);
	header.n_required_files	= action.nRequiredFiles;
	printf("> (%i, %i, %i)\n",header.asking_for_cost, header.message_length, header.n_required_files);
	
	if (write(sd, &header, sizeof(header)) < 0) 
	{
		perror("header:");
        exit(EXIT_FAILURE);
	}
	
	// SENDS SERVER THE COMMAND/ACTION TO BE EXECUTED
	if (write(sd, action.action, strlen(action.action)) < 0) 
	{
		perror("action:");
        exit(EXIT_FAILURE);
	}

	// SEND FILES TO SERVER
	if (action.nRequiredFiles > 0)
	{
		for (int i=0 ; i<action.nRequiredFiles ; i++)
		{
			FILE *fp = fopen(action.requiredFiles[i], "rb");
			
			// QUIT IF THE FILE DOES NOT EXIST
			if (fp == NULL)
				exit(EXIT_FAILURE);
			
			// GET THE FILESIZE IN BYTES
			fseek(fp, 0L, SEEK_END);
			int n_bytes = ftell(fp);
			fseek(fp, 0L, SEEK_SET);		
			
			char buffer[n_bytes];
			
			fread(&buffer, n_bytes, sizeof(char), fp);
			fclose(fp);


			// INFORM THE SERVER THE SIZE OF THE FILE TO RECEIVE AND THE FILENAME LENGTH
			printf("%s> sending '%s'%s\n", BLU, action.requiredFiles[i], RST);
			HeaderToServer req_file_header;
			req_file_header.asking_for_cost = 0;
			req_file_header.message_length = strlen(action.requiredFiles[i]);
			req_file_header.n_required_files = n_bytes;

			printf("%s> cost=%i, len=%i, size=%i%s\n", BLU, 
				req_file_header.asking_for_cost, 
				req_file_header.message_length,
				n_bytes, RST);
			
			if (write(sd, &req_file_header, sizeof(req_file_header)) < 0) 
			{
				perror("filsize:");
        		exit(EXIT_FAILURE);
			}

			// INFORM THE SERVER THE FILE DATA/CONTENT
			if (write(sd, buffer, n_bytes) < 0) 
			{
				perror("sending file:");
				exit(EXIT_FAILURE);
			}

			// INFORM THE SERVER THE NAME OF THE FILE
			if (write(sd, action.requiredFiles[i], strlen(action.requiredFiles[i])) < 0) 
        		exit(EXIT_FAILURE);
		}   
	}
}


/**
 * @brief 	Return the index to the cheapest host for executing @param argument,
 *			quoting on all remote server(s).
 * 
 * @param 	argument the argument to executed
 * @return 	int index to the cheapest host
 */
int get_cheapest_host(char *argument)
{
	int cheapest_host = 0;
	int lowest_cost = -1;

	HeaderToServer header;
	header.asking_for_cost = 1;
	header.message_length = strlen(argument);
	header.n_required_files = 0;

	for (int h=0 ; h<rackfile.nHosts ; h++)
	{
		int sd = establish_socket(rackfile.hosts[h].host, rackfile.hosts[h].port);
		
		if (write(sd, &header, sizeof(header)) < 0) 
			return -1;
		
		HeaderToServer reply;
		read(sd, &reply , 12);
		int cost = reply.asking_for_cost;
		
		shutdown(sd, SHUT_RDWR);
		close(sd);
		
		// REMEMBER THE REMOTE HOST RETURNING THE LOWEST COST TO RUN THE COMMAND
		if (cost < lowest_cost || lowest_cost == -1)
		{
			lowest_cost = cost;
			cheapest_host = h;
		}
	}
	return cheapest_host;
}

bool read_sockets(int *sds, int max_connections, fd_set read_fd_set, int *n_connected, int *outputs_received)
{
	bool error_in_actionset = false;
	for (int j=0 ; j<max_connections ; j++)
	{
		if (sds[j] >= 0 && FD_ISSET(sds[j], &read_fd_set)) 
		{
			printf(" %s----------------------------------------%s\n", MAG, RST);
			
			// 	DECRYPT HEADER
			HeaderFromServer response;
			read(sds[j], &response , sizeof(HeaderFromServer));
			
			int exit_status 			= response.exit_status;
			int output_len 				= response.output_len;
			int output_filesize 		= response.output_filesize;
			int output_filename_len 	= response.output_filename_len;
			int error_len 				= response.error_len;

			printf("< status:\n%d\n", exit_status);
			
			// REPORT STDOUT
			if (output_len > 0)
			{
				char output[ output_len ];
				read(sds[j], &output , output_len);
				printf("< stdout:\n");
				fprintf(stdout, "%s\n", output);
			}
			else
			{
				printf("< stdout:\n");
				fprintf(stdout,"\n");
			}

			// REPORT STDERR
			if (error_len > 0)
			{
				char error[ error_len ];
				read(sds[j], &error , error_len);
				printf("< stderr:\n");
				fprintf(stderr, "%s\n", error);
			}
			else
			{
				printf("< stderr:\n");
				fprintf(stderr,"\n");
			}

			// RECEIVING OUTPUT FILE
			if (output_filesize > 0 && output_filename_len > 0)
			{
				char file_data[output_filesize];
				read(sds[j], &file_data , output_filesize);
				
				char filename[output_filename_len];
				int bytes = read(sds[j], &filename , output_filename_len);
				filename[bytes] = '\0';

				int fp = open(filename, O_WRONLY | O_CREAT | O_TRUNC);
				write(fp, file_data, output_filesize);
				close(fp);
				
				printf("< output file name:\n%s\n", filename);
			}
			
			// ACTION FAILED
			if (exit_status != 0)
				error_in_actionset = true;
			
			shutdown(sds[j], SHUT_RDWR);
			close(sds[j]);
			sds[j] = -1;
			FD_CLR(sds[j], &read_fd_set);
			
			(*n_connected)--;
			
			(*outputs_received)++;
		}
	}

	return error_in_actionset;
}


void close_all_connections(int *sds, int max_connections)
{
	for (int i=0 ; i<max_connections ; i++)
	{
		if (sds[i] >= 0) 
		{
			shutdown(sds[i], SHUT_RDWR);
			close(sds[i]);
		}
	}
}

// void start_server_communication(bool is_remote, char action[])
// {
// 	char 	*host 	= NULL;
// 	int 	port 	= default_port;
// 	strncpy(host, "localhost", strlen("localhost"));

// 	//* IF ACTION IS REMOTE, THEN CHECK COST FROM EACH REMOTE SERVER
// 	if (!is_remote)
// 	{
// 		int cheapest_host = get_cheapest_host( action );
// 		strncpy(host, rackfile.hosts[cheapest_host].host, strlen(rackfile.hosts[cheapest_host].host));
// 		port = rackfile.hosts[cheapest_host].port;

// 		// EXECUTE ON CHEAPEST REMOTE HOST
// 		printf("%s --- REMOTE EXECUTION --- \n%s", YEL, RST);
// 		n_connected++;
// 		add_socket_connection(sds, max_connections, sd);
// 	}

// 	send_command_to_server(sd, action);
// 	//  IF ACTION IS LOCAL, EXECUTE ON LOCAL SERVER
// 	else
// 	{
// 		printf("%s --- LOCAL EXECUTION --- \n%s", YEL, RST);
// 		int sd = establish_socket("localhost", default_port);
// 		send_command_to_server(sd, *current_action);
// 		n_connected++;
// 		add_socket_connection(sds, max_connections, sd);
// 	}
// }

void add_socket_connection(int *sds, int max_connections, int sd)
{
	for (int i=0 ; i<max_connections ; i++)
	{
		// NOT CONNECTED
		if (sds[i] < 0)
		{
			sds[i] = sd;
			break;
		}
	}
}


int main(int argc, char *argv[])
{
    int opt;
    strcpy(host, "localhost");
    strcpy(rackfile_name, "Rakefile");
    while ((opt = getopt(argc, argv, "vhi:p:r:")) != -1) 
    {
        switch (opt) 
        {
            // HELP ( HOW TO USE )
            case 'h':
                printf("usage: ./rake-c -i <ip address> -p <port number> -r <rakefile>'\n");
                break;
            // RAKEFILE TO ANAYLSE
            case 'r':
                strcpy(rackfile_name, optarg);
                break;
            // IP ADDRESS
            case 'i':
                strcpy(host, optarg);
                break;
            // PORT NUMBER
            case 'p':
                port_num = atoi(optarg);
                break;
            // verbose - DEBUGGING
            case 'v':
                verbose = true;
                break;
        }
    }

    printf("\n"); 

    // EXTRACT INFO FROM "Rakefile" IN CURRENT DIRECTORY
    parse_file(rackfile_name);

    // DEBUGGING
    if (verbose)
    {
        printf(YEL);
        debug_rackfile();
        printf(RST);
    }
	
	bool error_in_actionset = false;
	struct timeval timeout;
	timeout.tv_usec = 1000;	// wait up to 0.1 seconds

	for (int i=0 ; i<rackfile.nActionSets && !error_in_actionset; i++)
	{
		int action_n = 0;
		int outputs_received = 0;
		int total_actions = rackfile.actionSets[i].nActions;
		bool still_waiting_for_outputs = true;

		fd_set read_fd_set;
		int max_connections	= rackfile.actionSets[i].nActions + 1;
		int n_connected 	= 0;
		int sds[max_connections];	// MAX NO. OF ACTION IN ACTIONSET + NO. OF SERVERS (DEFAULT + REMOTE)

		for (int c=0 ; c<max_connections ; c++)
			sds[c] = -1;

		if (verbose)
		{
			printf("%s --------------------------------------------------------------------------------%s\n", GRN, RST);
			printf("starting actionset%i\n", i + 1);
		}

		// KEEPS WAITING UNTIL ALL SERVERS HAVE RETURNED AN OUTPUT		
		while (still_waiting_for_outputs)
		{
			// RE-INIT CONNECTED SOCKETS
			FD_ZERO(&read_fd_set);
			for (int c=0 ; c<max_connections ; c++) 
				if (sds[c] >= 0) 
					FD_SET(sds[c], &read_fd_set);

			// EXECUTE ACTION, IF THERE ARE STILL UNEXECUTED ACTION(S) IN ACTIONSET
			if (action_n < total_actions)
			{
				Action *current_action = &(rackfile.actionSets[i].actions[action_n]);

				if (verbose)
					printf("%srunning %s%s\n", BLU, current_action->action, RST);

				// //* IF ACTION IS REMOTE, THEN CHECK COST FROM EACH REMOTE SERVER
				if (current_action->isRemote)
				{
					int cheapest_host;
					cheapest_host = get_cheapest_host( current_action->action ); // cost simulateonusly

					// EXECUTE ON CHEAPEST REMOTE HOST
					printf("%s --- REMOTE EXECUTION --- \n%s", YEL, RST);
					int sd = establish_socket(rackfile.hosts[cheapest_host].host, rackfile.hosts[cheapest_host].port);
					send_command_to_server(sd, *current_action);
					n_connected++;
					add_socket_connection(sds, max_connections, sd);
				}
			
				//  IF ACTION IS LOCAL, EXECUTE ON LOCAL SERVER
				else
				{
					printf("%s --- LOCAL EXECUTION --- \n%s", YEL, RST);
					int sd = establish_socket("localhost", default_port);
					send_command_to_server(sd, *current_action);
					n_connected++;
					add_socket_connection(sds, max_connections, sd);
				}

				action_n++;
			}
			
			if (n_connected > 0)
			{
				int nready = select(FD_SETSIZE, &read_fd_set, NULL, NULL, &timeout);
				
				if (nready > 0) 
				{
					if (read_sockets(sds, max_connections, read_fd_set, &n_connected, &outputs_received))
						error_in_actionset = true;
					if (outputs_received >= total_actions)
						still_waiting_for_outputs = false;
				}
			}
				
		}

		if (error_in_actionset)
		{
			printf("%serror detected in actionset - halting subsequent actionsets%s\n", RED, RST);
			break;
		}
		
		close_all_connections(sds, max_connections);
		
		sleep(1);
	}

    printf("\n");
    return EXIT_SUCCESS;
}

// cc -std=c99 -Wall -Werror -o client-c client-c.c && ./client-c
// cc -std=c99 -Wall -Werror -o rake-c rake-c.c && ./rake-c
