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

int char_at(char *string, char substring)
{
    char *ptr = strchr(string, substring);
    if (ptr == NULL)
        return -1;
    return ((int) (ptr - string));
}

void get_hosts(char* line)
{
   int len = strlen("HOSTS = ");
                    char *substring = line; //*
                    substring += len;      //* creates a pointer that points to a char that is immediately after 'Hosts = ' in line

                    const char *delimiter = " ";
                    char *host = strtok(substring, delimiter); 
                    
                    // LOOP THROUGH THE STRING TO EXTRACT ALL OTHER TOKENS i.e hosts
                    int *nHosts = &rackfile.nHosts;
                    while ( host != NULL ) 
                    {
                        // HAS A SPECIFIED PORT NUMBER
                        char *separator = strchr(host, ':'); 
                        if (separator != NULL)
                        {
                            *separator = '\0';
                            rackfile.hosts[*nHosts].port = atoi(separator + 1);
                            strcpy(rackfile.hosts[(*nHosts)++].host, host);
                        }
                        // NO SPECIFIED PORT NUMBER, SET DEFAULT PORT
                        else
                        {
                            rackfile.hosts[*nHosts].port = default_port;
                            strcpy(rackfile.hosts[(*nHosts)++].host, host);
                        }
                        host = strtok(NULL, delimiter);
                    }

}
void get_actionset(char* line,int* action_set_ind,int* n_action_set, int* action_ind){
    
  if (*action_set_ind + 1 == *n_action_set)
    {
        rackfile.actionSets[ *action_set_ind ].nActions = *action_ind;
        (*action_set_ind)++;
    }
    *action_ind = 0;
    (*n_action_set)++;
    int end_of_action_set = char_at(line, ':');
    strncpy(rackfile.actionSets[*action_set_ind].actionSetName, line, end_of_action_set);


}

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
bool starts_with(char *string, char *substring)
{
    return (strncmp(string, substring, strlen(substring)) == 0);
}




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


int count_leading_tabs(char *string)
{
    int index = 0;

    while (string[index] == '\t')
        index++;
    
    return index;
}

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

void parse_file(char *filename)
{

    if (verbose)
        printf("-- parsing %s\n\n", filename);

    FILE  *fp = fopen(filename, "r");
    char  line[BUFFER_SIZE];

    if (fp != NULL) 
    {
        strcpy(rackfile.filename, filename); // update filename in the rackfile struct
        int action_set_ind = 0; // keeps track of number of actionets in rakefile
        int action_ind    = 0; // keeps track of number of actions in each actionset
        int *n_action_set = &rackfile.nActionSets; // pointer to update number of actionsets in the rakefile struct
        while (fgets(line, sizeof(line), fp) != NULL) 
        {
            // STORE NON-EMPTY LINES
            if (!starts_with(line, "\n")) // skips empty lines
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
                    get_hosts(line);

                }
                // IF LINE STARTS WITH actionset, GET AND STORE Action
                else if (starts_with(line, "actionset"))
                {
                    get_actionset(line,&action_set_ind,n_action_set, &action_ind );
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



int main(){
    char* fn="Rakefile10";
    parse_file(fn);
    debug_rackfile();



}
