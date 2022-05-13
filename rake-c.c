#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

#include <string.h>
#include <sys/types.h>
#include <dirent.h>
#include <stdbool.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>	//inet_addr
#include <getopt.h>

#define     MAX_FILES_IN_DIRECTORY      128
#define     MAX_FILES_TO_PROCESS        128
#define     MAX_HOSTS                   32
#define     MAX_ACTIONS                 32
#define     MAX_ACTIONSETS              32
#define     MAX_REQUIREMENTS            32
#define     BUFFER_SIZE                 1024
#define     MAX_FILE_NAME               64
#define     MAX_LINE_LENGTH             1024

#define     RED                         "\033[0;31m"
#define     GRN                         "\033[0;32m"
#define     YEL                         "\033[0;33m"
#define     BLU                         "\033[0;34m"
#define     MAG                         "\033[0;35m"
#define     CYN                         "\033[0;36m"
#define     WHT                         "\033[0;37m"
#define     RESET                       "\033[0m"


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


void execute_all()
{
    printf("EXECUTING  -  %s\n", rackfile.filename);
    bool error_in_actionset = false;

    // ACTIONSETS
    for (int i=0 ; i<rackfile.nActionSets && !error_in_actionset ; i++)
    {
        // ACTIONs IN ACTIONSETS
        for (int a=0 ; a<rackfile.actionSets[i].nActions && !error_in_actionset ; a++)
        {
            int return_code = system(rackfile.actionSets[i].actions[a].action);
            
            // IF THERE IS AN ERROR IN RUNNING ACTION, STOP FOLLOWING ACTIONS
            if (return_code != 0)
            {
                printf(RED);
                printf("ERROR: %s\n", rackfile.actionSets[i].actions[a].action);
                printf(GRN);
                error_in_actionset = true;
            }
        }
    }

    printf("\n\n");
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


// int write_file_to_server(int sd, char message[])
// {
//     printf(GRN);
//     printf(" --> %s\n", message);
//     printf(RESET);

//     if (write(sd, message, strlen(message)) < 0) 
//         return EXIT_FAILURE;
        
//     // SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
//     char server_reply[1024];
//     read(sd, server_reply , 1024);
//     printf(CYN); printf(" <-- %s\n", server_reply); printf(RESET);
    
//     // SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
//     char action_status[1024];
//     read(sd, action_status , 1024);
//     printf(CYN); printf(" <-- %s\n", action_status); printf(RESET);

//     return atoi(action_status);
// }

int write_file_to_server(int sd, char message[])
{
    printf(GRN);
    printf(" --> %s\n", message);
    printf(RESET);

    if (write(sd, message, strlen(message)) < 0) 
        return EXIT_FAILURE;
        
    // SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
    char server_reply[1024];
    read(sd, server_reply , 1024);
    printf(CYN); printf(" <-- %s\n", server_reply); printf(RESET);
    
    // SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
    char action_status[1024];
    read(sd, action_status , 1024);
    printf(CYN); printf(" <-- %s\n", action_status); printf(RESET);

	shutdown(sd, SHUT_RDWR);
    close(sd);

    return atoi(action_status);
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
/**
 * @brief Return the cost of executing a command on the specified server.
 * 
 * @param server 
 * @param port 
 * @return int 
 */
int get_cost_from_server(char *host, int port)
{
	int sd = establish_socket(host, port);
    
	if (write(sd, "cost?", strlen("cost?")) < 0) 
		return -1;

	// SERVER INFORMS CLIENT IF MESSAGE WAS RECEIVED
    char server_reply[1024];
    read(sd, server_reply , 1024);

    shutdown(sd, SHUT_RDWR);
    close(sd);

	return atoi(server_reply);
}


int main(int argc, char *argv[])
{
    int opt;
    strcpy(host, "localhost");
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
            // VERBOSE - DEBUGGING
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
        printf(RESET);
    }


	bool error_in_actionset = false;
	for (int i=0 ; i<rackfile.nActionSets && !error_in_actionset; i++)
    {
        for (int j=0 ; j<rackfile.actionSets[i].nActions && !error_in_actionset; j++)
        {
			// * IF ACTION IS REMOTE, THEN CHECK COST FROM EACH SERVER
			if (rackfile.actionSets[i].actions[j].isLocal)
			{
				int cheapest_host = 0;
				int lowest_cost = 1000;

				for (int h=0 ; h<rackfile.nHosts ; h++)
				{
					int cost = get_cost_from_server(rackfile.hosts[h].host, rackfile.hosts[h].port);
					if (verbose)
						printf("(%s, %i) = %i\n",rackfile.hosts[h].host, rackfile.hosts[h].port, cost);
					
					// REMEMBER THE REMOTE HOST RETURNING THE LOWEST COST TO RUN THE COMMAND
					if (cost < lowest_cost)
					{
						lowest_cost = cost;
						cheapest_host = h;
					}
				}

				// EXECUTE ON CHEAPEST REMOTE HOST
				printf("%s --- REMOTE EXECUTION --- \n%s", YEL, RESET);
				printf("executing order on %s (%i)\n", rackfile.hosts[cheapest_host].host, cheapest_host);
				int sd = establish_socket(rackfile.hosts[cheapest_host].host, rackfile.hosts[cheapest_host].port);
				if (write_file_to_server(sd, rackfile.actionSets[i].actions[j].action) != 0)
					error_in_actionset = true;
				// execute_on_server( hosts[cheapest_host] , action[0].split("remote-")[1]);
			}
			// * ELSE, EXECUTE ON LOCAL SERVER
			else
			{
				printf("%s --- LOCAL EXECUTION --- \n%s", YEL, RESET);
				int sd = establish_socket("localhost", default_port);
				if (write_file_to_server(sd, rackfile.actionSets[i].actions[j].action) != 0)
					error_in_actionset = true;
				// execute_on_server( ('localhost' , DEFAULT_PORT) , action[0])
			}
		}
	}

	if (true)		//! DELETE
		return 0;	//! DELETE

    // EXECUTING

	//  LOCATE INFORMATION ABOUT THE REQUIRED HOST (ITS IP ADDRESS)
	// struct hostent     *hp = gethostbyname("10.20.162.197");
	struct hostent     *hp = gethostbyname(host);
	// struct hostent     *hp = gethostbyname("localhost");
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
    // server.sin_addr.s_addr = inet_addr(hp->h_addr);
    memcpy(&server.sin_addr, hp->h_addr, hp->h_length);
    // server.sin_addr.s_addr = inet_addr("10.20.162.197");
	// server.sin_family = AF_INET;
    server.sin_family  = hp->h_addrtype;
	server.sin_port = htons( port_num );

    //  CONNECT TO SERVER
    // //  FIND AND CONNECT TO THE SERVICE ADVERTISED WITH "THREEDsocket"
    if (connect(sd, (struct sockaddr *)&server, sizeof(server)) < 0) 
    {
        perror("rlogin: connect");
        exit(4);
    }

    // bool error_in_actionset = false;
    // for (int i=0 ; i<rackfile.nActionSets && !error_in_actionset; i++)
    // {
    //     for (int j=0 ; j<rackfile.actionSets[i].nActions && !error_in_actionset; j++)
    //     {
    //         // EXECUTE ACTION ON SERVER
    //         if (rackfile.actionSets[i].actions[j].isLocal)
    //         {
    //             if (write_file_to_server(sd, rackfile.actionSets[i].actions[j].action) != 0)
    //             {
    //                 error_in_actionset = true;
    //                 printf("  ERROR IN SERVER: STOP EXECUTING REMAINING ACTION(S)\n");
    //             }
    //         }
    //         // EXECUTE ACTION ON LOCAL MACHINE
    //         else
    //         {
    //             printf(RESET);
    //             if (system(rackfile.actionSets[i].actions[j].action))
    //             {
    //                 error_in_actionset = true;
    //                 printf("  ERROR ON LOCAL: STOP EXECUTING REMAINING ACTION(S)\n");
    //             }
    //         }
    //     }
    // }
    shutdown(sd, SHUT_RDWR);
    close(sd);

    printf("\n");
    return EXIT_SUCCESS;
}

// cc -std=c99 -Wall -Werror -o client-c client-c.c && ./client-c
// cc -std=c99 -Wall -Werror -o rake-c rake-c.c && ./rake-c
