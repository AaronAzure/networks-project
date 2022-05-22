#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/time.h>
#include <sys/stat.h>
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
    bool    isLocal;
    
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


extern int errno;

char file_path[MAX_FILE_NAME];

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
    int	exit_status;
    int	filename_len;	// FILENAME LENGTH OF CREATED/MODIFIED FILE
    int	output_size;	// LENGTH OF OUTPUT (STDOUT) OR CREATED/MODIFIED FILE SIZE
    int	error_size;		// LENGTH OF OUTPUT (STDERR)
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
            printf(" - (%s)\t|%s|\n", rackfile.actionSets[i].actions[a].isLocal ? "true" : "false", rackfile.actionSets[i].actions[a].action);
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
                                rackfile.actionSets[ action_set_ind ].actions[action_ind].isLocal = true;
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

char *strcat_realloc(char *string1, const char *string2)
{
    int string1_len = strlen(string1);
    int string2_len = strlen(string2);
    int combined_len = string1_len + string2_len + 1;	// '\0' character byte

    string1 = realloc(string1, combined_len);

    memcpy(string1 + string1_len, string2, string2_len + 1);

    return string1;
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
void write_file_to_server(int sd, Action action)
{
	//! --------------------------------------------------
	// def execute_on_server(server_port_tuple, argument, requirements=None):
	// # ADDS FILE REQUIREMENTS TO message STRING, SEPARATED BY ' Requirements: '.
	// char *message = (char *)calloc(strlen(argument) + 1, sizeof(char));
	
	// INFORMS SERVER REGARDING THE PAYLOAD SIZE
	HeaderToServer header;
	
	header.asking_for_cost = 0;
	header.message_length = strlen(action.action);
	header.n_required_files = action.nRequiredFiles;
	
	// printf("%spreparing to write to %s\n", BLU, RST);
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
			struct stat sb;

			if (stat(action.requiredFiles[i], &sb) == -1) 
			{
				perror("stat");
				exit(EXIT_FAILURE);
			}

			printf("%s> sending %s%s\n", BLU, action.requiredFiles[i], RST);

			// INFORM THE SERVER THE SIZE OF THE FILE TO RECEIVE
			HeaderToServer req_file_header;
			req_file_header.asking_for_cost = 0;
			req_file_header.message_length = strlen(action.requiredFiles[i]);
			req_file_header.n_required_files = (int)sb.st_size;

			printf("%s> filesize = %i%s\n", BLU, (int) sb.st_size, RST);
			if (write(sd, &req_file_header, sizeof(req_file_header)) < 0) 
			{
				perror("filsize:");
        		exit(EXIT_FAILURE);
			}
			
			// SEND FILE NAME
			printf("%s> sending %s%s\n", BLU, action.requiredFiles[i], RST);
			// printf("%s> filename = %i%s\n", BLU, (int) sb.st_size, RST);
			if (write(sd, action.requiredFiles[i], sizeof(action.requiredFiles[i])) < 0) 
        		exit(EXIT_FAILURE);
				
			
			FILE  *fp = fopen(action.requiredFiles[i], "rb");
			char file_content[req_file_header.n_required_files];
			fgets(file_content, sizeof(file_content), fp);
			printf("%s> sending file!!!%s\n", BLU, RST);
			if (write(sd, file_content, strlen(file_content)) < 0) 
			{
				perror("sending file:");
				exit(EXIT_FAILURE);
			}
			
			printf("%s> SENT!!!%s\n", BLU, RST);
			fclose(fp);
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

//! delete
void none()
{
    // int sds[rackfile.nHosts];
    // fd_set read_fd_set;
	// FD_ZERO(&read_fd_set);

    // // INITIALISE ALL REMOTE SOCKETS
	// for (int h=0 ; h<rackfile.nHosts ; h++)
    // {
	// 	int sd = establish_socket(rackfile.hosts[h].host, rackfile.hosts[h].port);
	// 	sds[h] = sd;
	// 	FD_SET(sd, &read_fd_set);
	// 	if (write(sd, "cost?", strlen("cost?")) < 0) 
	// 		return -1;
    // }

	// struct timeval timeout;
	// timeout.tv_sec  = 10;             // wait up to 10 seconds
	// timeout.tv_usec =  0;

    // int cost_received = 0;
    // int lowest_cost = -1;
    // int cheapest_host = -1;

	// bool keep_going = true;
    // while (keep_going)
    // {
    //     // init fd_set
    //     for (int h=0 ; h<rackfile.nHosts ; h++)
    //     {
    //         FD_SET(sds[h], &read_fd_set);
    //     }

	// 	// READ FILE DESCRIPTORS
	// 	// if (select(FD_SETSIZE, &read_fd_set, NULL, NULL, &timeout) < 0) 
	// 	if (select(FD_SETSIZE, &read_fd_set, NULL, NULL, NULL) < 0) 
	// 	{
    //         exit(EXIT_FAILURE);
    //     }
		
    //     for (int h=0 ; h<rackfile.nHosts ; h++)
    //     {
    //         if (FD_ISSET(sds[h], &read_fd_set)) 
    //         {
	// 			char server_cost[2048];
    //             read(sds[h], server_cost , 2048);
				
	// 			int reply_cost = atoi(server_cost);
				
	// 			// REMEMBER CHEAPEST HOST TO RUN COMMAND/ACTION
	// 			if (reply_cost < lowest_cost || lowest_cost == -1)
	// 			{
	// 				lowest_cost = reply_cost;
	// 				cheapest_host = h;
	// 			}

	// 			cost_received++;
	// 			if (cost_received >= rackfile.nHosts)
	// 				keep_going = false;
	// 			FD_CLR(sds[h], &read_fd_set);
	// 		}
	// 	}
	// }
	
	// /* Last step: Close all the sockets */
	// for (int h=0 ; h<rackfile.nHosts ; h++)
	// {
	// 	if (sds[h] >= 0) 
	// 	{
	// 		shutdown(sds[h], SHUT_RDWR);
	// 		close(sds[h]);
	// 	}
	// }

	// return cheapest_host;
}
//! delete
void non_blocking()
{
	// int max_connections	= rackfile.actionSets[i].nActions + 1;
	// int n_connected 	= 0;
    // int sds[max_connections];	// MAX NO. OF ACTION IN ACTIONSET + NO. OF SERVERS (DEFAULT + REMOTE)
	
    // fd_set read_fd_set;
	// FD_ZERO(&read_fd_set);

    // // INITIALISE ALL REMOTE SOCKETS
	// for (int i=0 ; i<max_connections ; i++)
	// 	sds[h] = -1;
	// // FD_SET(sd, &read_fd_set);
	// // if (write(sd, "cost?", strlen("cost?")) < 0) 

	// struct timeval timeout;
	// timeout.tv_sec  = 0;             // wait up to 0.5 seconds
	// timeout.tv_usec = 5000;

	// bool keep_going = true;
    // while (keep_going)
    // {
	// 	FD_ZERO(&read_fd_set);

    //     // re-init fd_set
    //     for (int i=0 ; i<max_connections ; i++)
    //     {
	// 		// if (sds[i] >= 0 && FD_ISSET(i, &read_fd_set))
	// 		if (sds[i] >= 0)
    //         	FD_SET(i, &read_fd_set);
    //     }

	// 	// READ FILE DESCRIPTORS
	// 	// if (select(FD_SETSIZE, &read_fd_set, NULL, NULL, NULL) < 0) 
	// 	if (select(FD_SETSIZE, &read_fd_set, NULL, NULL, &timeout) > 0) 
	// 	{
	// 		for (int i=0 ; i<max_connections ; i++)
	// 		{
	// 			if (FD_ISSET(sds[i], &read_fd_set)) 
	// 			{
	// 				char server_cost[2048];
	// 				read(sds[i], server_cost , 2048);
					
	// 				int reply_cost = atoi(server_cost);
					
	// 				// REMEMBER CHEAPEST HOST TO RUN COMMAND/ACTION
	// 				if (reply_cost < lowest_cost || lowest_cost == -1)
	// 				{
	// 					lowest_cost = reply_cost;
	// 					cheapest_host = i;
	// 				}

	// 				cost_received++;
	// 				if (cost_received >= rackfile.nHosts)
	// 					keep_going = false;
	// 				FD_CLR(sds[i], &read_fd_set);
	// 			}
	// 		}
	// 	}
	// }
	
	// /* Last step: Close all the sockets */
	// for (int i=0 ; i<max_connections ; i++)
	// {
	// 	if (sds[i] >= 0) 
	// 	{
	// 		shutdown(sds[i], SHUT_RDWR);
	// 		close(sds[i]);
	// 	}
	// }

	// return cheapest_host;
}
//! delete
void read_sockets(int *n_connected, int max_connections)
{
	// for (int i=0 ; i<max_connections ; i++)
	// {
	// 	if (sds[i] >= 0 && FD_ISSET(sds[i], &read_fd_set)) 
	// 	{
	// 		char server_cost[2048];
	// 		read(sds[i], server_cost , 2048);
			
	// 		int reply_cost = atoi(server_cost);
			
	// 		// REMEMBER CHEAPEST HOST TO RUN COMMAND/ACTION
	// 		// if (reply_cost < lowest_cost || lowest_cost == -1)
	// 		// {
	// 		// 	lowest_cost = reply_cost;
	// 		// 	cheapest_host = i;
	// 		// }

	// 		// cost_received++;
	// 		// if (cost_received >= rackfile.nHosts)
	// 		// 	keep_going = false;
	// 		FD_CLR(sds[i], &read_fd_set);
	// 	}
	// }
}

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

	// int socket_desc = establish_socket("localhost", 12345);
	
	// HeaderToServer header;
	// header.asking_for_cost = 1;
	// header.message_length = 15;
	// printf("-- %lu\n", sizeof(struct HeaderToServer));
	
	// if (write(socket_desc, &header, sizeof(header)) < 0) 
	// 	return -1;
	// else
	// {
	// 	HeaderToServer response;
	// 	read(socket_desc, &response , 8);
	// 	printf("-- (%i, %i)\n", response.asking_for_cost, response.message_length);
	// 	printf("-- %lu\n", sizeof(response));
	// 	close(socket_desc);

	// }
	
	bool error_in_actionset = false;
	struct timeval timeout;
	// timeout.tv_sec  = 1;             // wait up to 0.5 seconds
	timeout.tv_usec = 1000;

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
			// printf('starting', actionset);
			// printf(f"{GRN}{rake_dict[actionset]}{RST}");
		}

		while (still_waiting_for_outputs)
		{
			FD_ZERO(&read_fd_set);
			for (int c=0 ; c<max_connections ; c++) 
				if (sds[c] >= 0) 
					FD_SET(sds[c], &read_fd_set);

			if (action_n < total_actions)
			{
				// char *action = &rackfile.actionSets[i].actions[j].action;
				Action *current_action = &(rackfile.actionSets[i].actions[action_n]);

				if (verbose)
					printf("%srunning %s%s\n", BLU, current_action->action, RST);
				
				// CHECK IF ACTION HAS REQUIREMENTS

				// if (action.nRequiredFiles > 1) // HAS REQUIREMENT FILES
					// requirements = action[1].split()[1:]

				//* IF ACTION IS REMOTE, THEN CHECK COST FROM EACH REMOTE SERVER
				if (current_action->isLocal)
				{
					int cheapest_host;
					cheapest_host = get_cheapest_host( current_action->action ); // cost simulateonusly

					// EXECUTE ON CHEAPEST REMOTE HOST
					printf("%s --- REMOTE EXECUTION --- \n%s", YEL, RST);
					// todo sd = execute_on_server( hosts[cheapest_host] , argument , requirements )
					int sd = establish_socket(rackfile.hosts[cheapest_host].host, rackfile.hosts[cheapest_host].port);
					write_file_to_server(sd, *current_action);
					// print(f"{BLU}> {argument} {requirements}{RST}")
					n_connected++;
					add_socket_connection(sds, max_connections, sd);
				}
			
				//  IF ACTION IS LOCAL, EXECUTE ON LOCAL SERVER
				else
				{
					printf("%s --- LOCAL EXECUTION --- \n%s", YEL, RST);
					// todo sd = execute_on_server( ( 'localhost' , DEFAULT_PORT ) , *current_action[0], requirements )
					int sd = establish_socket("localhost", default_port);
					write_file_to_server(sd, *current_action);
					// print(f"{BLU}> {current_action[0]} {requirements}{RST}")
					n_connected++;
					add_socket_connection(sds, max_connections, sd);
				}

				action_n++;
			}
			
			if (n_connected > 0)
			{
				int nready = select(FD_SETSIZE, &read_fd_set, NULL, NULL, &timeout);
				// printf(" n_connected=%i\n",n_connected);
				if (nready > 0) 
				{
					for (int j=0 ; j<max_connections ; j++)
					{
						// printf("%d ")
						if (sds[j] >= 0 && FD_ISSET(sds[j], &read_fd_set)) 
						{
							printf(" %s----------------------------------------%s\n", MAG, RST);
							// print(MAG, f"from {sd.getpeername()}", RST)
							
							// 	DECRYPT HEADER
							HeaderFromServer response;
							read(sds[j], &response , sizeof(HeaderFromServer));
							int exit_status 	= response.exit_status;
							int filename_len 	= response.filename_len;
							int output_size 	= response.output_size;
							int error_size 		= response.error_size;

							printf("< status:\n%d\n", exit_status);
							
							// NOT RECEIVING OUTPUT FILE
							if (filename_len == 0)
							{
								// output = sd.recv( output_size ).decode("utf-8")
								char output[ output_size ];
								read(sds[j], &output , output_size);
								// err = sd.recv( err_size).decode("utf-8")
								char error[ error_size ];
								read(sds[j], &error , error_size);
								
								if (strcmp(output, "") != 0)
									printf("< output:\n%s\n", output);
								else
									printf("< output:\nNone\n");

								if (strcmp(error, "") != 0)
									printf("< err:\n%s\n", error);
								else
									printf("< err:\nNone\n");
							}
							// RECEIVING OUTPUT FILE
							else
							{
								char outputname[ filename_len ];
								read(sds[j], &outputname , filename_len);

								char output[ output_size ];
								read(sds[j], &output , output_size);

								char error[ error_size ];
								read(sds[j], &error , error_size);
								
								printf("< output file name:\n%s\n", outputname);
								if (strcmp(error, "") != 0)
									printf("< err:\n%s\n", error);
								else
									printf("< err:\nNone\n");

								// file = open(outputname, 'wb')
								FILE  *fp = fopen(outputname, "wb");
								fwrite(output, sizeof(output), 1, fp);
								
								fclose(fp);
							}
							
							// ACTION FAILED
							if (exit_status != 0)
								error_in_actionset = true;
							
							shutdown(sds[j], SHUT_RDWR);
							close(sds[j]);
							sds[j] = -1;
							FD_CLR(sds[j], &read_fd_set);
							
							n_connected--;
							
							outputs_received++;
							if (outputs_received >= total_actions)
								still_waiting_for_outputs = false;
						}
						// READ FROM SERVER, WHILST CONNECTED
						// for sd in exceptional:
							// error_in_actionset = true;
							// still_waiting_for_outputs = false;
							// sd.close()
							// inputs.remove(sd)
					}
				}
			}
				
		}

		if (error_in_actionset)
		{
			printf("%serror detected in actionset - halting subsequent actionsets%s\n", RED, RST);
			break;
		}
		
		for (int i=0 ; i<max_connections ; i++)
		{
			if (sds[i] >= 0) 
			{
				shutdown(sds[i], SHUT_RDWR);
				close(sds[i]);
			}
		}
	}

	// bool error_in_actionset = false;
	// for (int i=0 ; i<rackfile.nActionSets && !error_in_actionset; i++)
	// {
	// 	for (int j=0 ; j<rackfile.actionSets[i].nActions && !error_in_actionset; j++)
	// 	{
	// 		int cheapest_host;
	// 		if (rackfile.actionSets[i].actions[j].isLocal)
	// 			cheapest_host = get_cheapest_host();
	// 		switch ( fork() )
	// 		{
	// 			//* ERROR
	// 			case -1:
	// 				exit(EXIT_FAILURE);
	// 				break;
	// 			//* CHILD PROCESS
	// 			case 0:
	// 				// * IF ACTION IS REMOTE, THEN CHECK COST FROM EACH SERVER
	// 				if (rackfile.actionSets[i].actions[j].isLocal)
	// 				{

	// 					// EXECUTE ON CHEAPEST REMOTE HOST
	// 					printf("%s --- REMOTE EXECUTION --- \n%s", YEL, RST);
	// 					int sd = establish_socket(rackfile.hosts[cheapest_host].host, rackfile.hosts[cheapest_host].port);
	// 					int return_val = write_file_to_server(sd, rackfile.actionSets[i].actions[j].action);
	// 					// printf("%sret - %i\n%s", YEL, return_val, RST);
	// 					exit(return_val);
	// 				}
	// 				else
	// 				{
	// 					printf("%s --- LOCAL EXECUTION --- \n%s", YEL, RST);
	// 					int sd = establish_socket("localhost", default_port);
	// 					int return_val = write_file_to_server(sd, rackfile.actionSets[i].actions[j].action);
	// 					// printf("%sret - %i\n%s", YEL, return_val, RST);
	// 					exit(return_val);
	// 				}
	// 				break;
	// 			//* PARENT PROCESS
	// 			default:
	// 				break;
	// 		}
	// 	}

	// 	pid_t child;
	// 	int status;
	// 	// WAIT FOR ALL CHILD PROCESS TO EXIT
	// 	while ((child = wait(&status)) > 0)
	// 		if (WEXITSTATUS(status) != 0)
	// 			error_in_actionset = true;

	// 	if (error_in_actionset)
	// 		printf("error detected in actionset - halting subsequent actionsets\n");
	// }

    printf("\n");
    return EXIT_SUCCESS;
}

// cc -std=c99 -Wall -Werror -o client-c client-c.c && ./client-c
// cc -std=c99 -Wall -Werror -o rake-c rake-c.c && ./rake-c
