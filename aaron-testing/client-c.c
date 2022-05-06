#include <stdio.h>
#include <stdlib.h>
#include  <unistd.h>
#include  <sys/wait.h>

#include  <string.h>
#include  <sys/types.h>
#include  <dirent.h>
#include  <stdbool.h>

#define     MAX_FILES_IN_DIRECTORY      128
#define     MAX_FILES_TO_PROCESS        128
#define     MAX_HOSTS                   32
#define     MAX_ACTIONS                 32
#define     BUFFER_SIZE                 512
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
    char    actions[BUFFER_SIZE];
    
    int     nRequirements;
    char    requirements[BUFFER_SIZE][BUFFER_SIZE];
} Action;


typedef struct ActionSet
{
    char    actionSetName[BUFFER_SIZE];
    
    int     nActions;
    char    actions[BUFFER_SIZE][BUFFER_SIZE];   //  each VALID line
} ActionSet;


typedef struct Rackfile
{
    int         port;
    char        filename[MAX_FILE_NAME];

    int         nHosts;
    char        hosts[MAX_HOSTS][BUFFER_SIZE];

    int         nActionSets;
    ActionSet   actionSets[MAX_ACTIONS];    //! ERROR
} Rackfile;


extern int errno ;

char file_path[MAX_FILE_NAME];

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
    for (int k=0 ; k<rackfile.nActionSets && !error_in_actionset ; k++)
    {
        // ACTIONs IN ACTIONSETS
        for (int a=0 ; a<rackfile.actionSets[k].nActions && !error_in_actionset ; a++)
        {
            int return_code = system(rackfile.actionSets[k].actions[a]);
            // printf("  -> %i\n", return_code);

                // int errnum;
                // errnum = errno;
                // fprintf(stderr, "Value of errno: %d\n", errno);
                // perror("Error printed by perror");
                // fprintf(stderr, "Error opening file: %s\n", strerror( errnum ));
            
            // IF THERE IS AN ERROR IN RUNNING ACTION, STOP FOLLOWING ACTIONS
            if (return_code != 0)
            {
                printf(RED);
                printf("ERROR: %s\n", rackfile.actionSets[k].actions[a]);
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

    // PORT NUMBER
    printf("port num:\n - %i\n", rackfile.port);

    // HOST(S)
    printf("hosts:\n");
    for (int h=0 ; h<rackfile.nHosts ; h++)
        printf(" - %s\n", rackfile.hosts[h]);

    // ACTIONSETS
    for (int k=0 ; k<rackfile.nActionSets ; k++)
    {
        printf("%s:\n", rackfile.actionSets[k].actionSetName);
        for (int a=0 ; a<rackfile.actionSets[k].nActions ; a++)
            printf(" - %s", rackfile.actionSets[k].actions[a]);
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
    printf("-- parsing %s\n", filename);
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
            // if (strncmp("\n", line, strlen("\n")) != 0) // starting with a new line char
            if (strcmp(line, "\n") != 0) // is a newline character
            {
                // printf(" -> %i\n", *nActionSet);
                int commentCharIndex = char_at(line, '#');

                // IF LINE STARTS WITH PORT, GET AND STORE PORT NUMBER
                if (starts_with(line, "PORT"))
                {
                    char *last_word = NULL;
                    last_word = get_last_word(line);
                    rackfile.port = atoi(last_word);
                }
                // IF LINE STARTS WITH HOSTS, GET AND STORE HOST(S)
                else if (starts_with(line, "HOSTS"))
                {
                    int len = strlen("HOSTS = ");
                    char *substring = line;
                    substring += len;

                    const char *delimiter = " ";
                    char *token = strtok(substring, delimiter);
                    
                    // loop through the string to extract all other tokens
                    int *nHosts = &rackfile.nHosts;
                    while ( token != NULL ) 
                    {
                        strcpy(rackfile.hosts[(*nHosts)++], token);
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
                // IF THERE IS A COMMENT SYMBOL, STORE ENTIRE LINE UNTIL FIRST '#'
                else if (commentCharIndex != -1)
                {
                    strncpy(rackfile.actionSets[ action_set_ind ].actions[action_ind], line, commentCharIndex);
                    strcat(rackfile.actionSets[ action_set_ind ].actions[action_ind], "\n");
                    action_ind++;
                }
                // STORE ENTIRE LINE
                else
                {
                    trim_leading(line);
                    strcpy(rackfile.actionSets[ action_set_ind ].actions[action_ind], line);
                    action_ind++;
                }
            }
        }
        fclose(fp);
        rackfile.actionSets[ action_set_ind ].nActions = action_ind;
    }
    else
    {
        printf("!! ERROR: could not open %s\n", filename);
    }
}


int main(int argc, char *argv[])
{
    printf("\n");

    printf(CYN);

    // EXTRACT INFO FROM "Rakefile" IN CURRENT DIRECTORY
    if (argc == 1)
    {
        printf("Found files at current directory:\n");
        parse_file("Rakefile");
        strcpy(file_path, "");
    }

    // EXTRACT INFO FROM SPECIFIED FILE ( FROM COMMAND LINE ARGS )
    else if (argc > 1)
    {
        printf("Found files at %s:\n", argv[1]);
        parse_file(argv[1]);
        strcpy(file_path, argv[1]);
        strcat(file_path, "/");
    }

    printf(RESET); printf("\n");


    // DEBUGGING
    printf(YEL);
    debug_rackfile();
    printf(RESET);

    // EXECUTING
    printf(GRN);
    execute_all();
    printf(RESET);


    printf("\n");
    return EXIT_SUCCESS;
}

// cc -std=c99 -Wall -Werror -o client-c client-c.c && ./client-c
