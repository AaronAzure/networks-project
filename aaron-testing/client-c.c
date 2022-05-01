#include <stdio.h>
#include <stdlib.h>

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


typedef struct ActionSet
{
    char    actionName[BUFFER_SIZE];
    
    int     nActions;
    char    actions[BUFFER_SIZE][BUFFER_SIZE];   //  each VALID line
} ActionSet;


typedef struct Rackfile
{
    int         port;

    int         nHosts;
    char        hosts[MAX_HOSTS][BUFFER_SIZE];

    int         nActionSets;
    ActionSet   actionSets[MAX_ACTIONS];    //! ERROR
    // char    actions[BUFFER_SIZE][BUFFER_SIZE];   //  each VALID line
} Rackfile;


int n_files_in_dir = 0;
char *files_in_dir[MAX_FILES_TO_PROCESS];

int n_rackfiles = 0;
Rackfile rackfiles[MAX_FILES_TO_PROCESS];


// -------------------------------------------------------------------
// ---------------------------- METHODS ------------------------------

/**
 * @brief Remove leading whitespace characters from string
 * 
 * @param str - string to remove leading whitespace characters
 */
void trim_leading(char * str)
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
 * @param line      string to be analysed
 * @return char*    last word of string
 */
char *get_last_word(char *line)
{
    const char *delimiter = " ";

    // Extract the first token
    char *token = strtok(line, delimiter);
    char *last_word = NULL;
    
    // loop through the string to extract all other tokens
    while( token != NULL ) 
    {
        last_word = token;
        token = strtok(NULL, delimiter);
    }

    return last_word;
}


int min(int x, int y)
{
    return (x < y ? x : y);
}

int max(int x, int y)
{
    if (x > y)
        return x;
    return y;
    // return (x > y ? x : y);
}


/**
 * @brief   Find first occurrence of specified character in string
 * 
 * @param line      string to be analysed
 * @param toFind    character to be found
 * @return int      index of first occurrence of specified character
 */
int char_at(char *line, char toFind)
{
    char *ptr = strchr(line, toFind);
    if (ptr == NULL)
        return -1;
    return ((int) (ptr - line));
}

/**
 * @brief   (Debugging purposes) 
 *          For each anaylsed file:
 *           - Print port number
 *           - Print all host(s)
 *           - Print all actionset(s)
 * 
 */
void read_rackfile()
{
    for (int i=0 ; i<n_rackfiles ; i++)
    {
        printf(YEL);

        // PORT NUMBER
        printf("port num:\n - %i\n", rackfiles[i].port);

        // HOST(S)
        printf("hosts:\n");
        for (int h=0 ; h<rackfiles[i].nHosts ; h++)
            printf(" - %s\n", rackfiles[i].hosts[h]);

        // ACTIONSETS
        for (int k=0 ; k<rackfiles[i].nActionSets ; k++)
        {
            printf("%s", rackfiles[i].actionSets[k].actionName);
            for (int a=0 ; a<rackfiles[i].actionSets[k].nActions ; a++)
                printf(" - %s", rackfiles[i].actionSets[k].actions[a]);
                // printf("%s", rackfiles[i].actions[a]);
        }

        printf("\n\n");
    }
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
    FILE  *fp = fopen(filename, "r");
    char  line[BUFFER_SIZE];

    if (fp != NULL) 
    {
        int nAction    = 0;
        int nActionSet = 0;
        while (fgets(line, sizeof(line), fp) != NULL) 
        {
            // if (strcmp(line, "\n") != 0)
            //     printf("%s", line);

            // STORE NON-EMPTY LINES
            // if (strncmp("\n", line, strlen("\n")) != 0) // starting with a new line char
            if (strcmp(line, "\n") != 0) // is a newline character
            {
                // int *nActionSet = &rackfiles[n_rackfiles].nActionSets;
                // int *nAction    = &rackfiles[n_rackfiles].actionSets[*nActionSet].nActions;
                // printf(" -> %i\n", *nActionSet);
                int commentCharIndex = char_at(line, '#');

                // IF LINE STARTS WITH PORT, GET AND STORE PORT NUMBER
                if (strncmp("PORT", line, strlen("PORT")) == 0)
                {
                    char *last_word = NULL;
                    last_word = get_last_word(line);
                    rackfiles[n_rackfiles].port = atoi(last_word);
                }
                // IF LINE STARTS WITH HOSTS, GET AND STORE HOST(S)
                else if (strncmp("HOSTS = ", line, strlen("HOSTS = ")) == 0)
                {
                    int len = strlen("HOSTS = ");
                    char *substring = line;
                    substring += len;

                    const char *delimiter = " ";
                    char *token = strtok(substring, delimiter);
                    
                    // loop through the string to extract all other tokens
                    int *nHosts = &rackfiles[n_rackfiles].nHosts;
                    while ( token != NULL ) 
                    {
                        strcpy(rackfiles[n_rackfiles].hosts[(*nHosts)++], token);
                        token = strtok(NULL, delimiter);
                    }

                }
                // IF LINE STARTS WITH actionset, GET AND STORE Action
                else if (strncmp("actionset", line, strlen("actionset")) == 0)
                {
                    strcpy(rackfiles[n_rackfiles].actionSets[nActionSet].actionName, line);
                    rackfiles[n_rackfiles].actionSets[ max( nActionSet - 1, 0 ) ].nActions = nAction;
                    nAction = 0;
                    nActionSet++;
                }
                // IF THERE IS A COMMENT SYMBOL, STORE ENTIRE LINE UNTIL FIRST '#'
                else if (commentCharIndex != -1)
                {
                    strncpy(rackfiles[n_rackfiles].actionSets[ max( nActionSet - 1, 0 ) ].actions[nAction], line, commentCharIndex);
                    strcat(rackfiles[n_rackfiles].actionSets[ max( nActionSet - 1, 0 ) ].actions[nAction], "\n");
                    printf("~ %s\n", rackfiles[n_rackfiles].actionSets[ max( nActionSet - 1, 0 ) ].actions[nAction]);
                    nAction++;
                }
                // STORE ENTIRE LINE
                else
                {
                    trim_leading(line);
                    strcpy(rackfiles[n_rackfiles].actionSets[ max( nActionSet - 1, 0 ) ].actions[nAction], line);
                    printf("~ %s\n", rackfiles[n_rackfiles].actionSets[ max( nActionSet - 1, 0 ) ].actions[nAction]);
                    nAction++;
                }
            }
        }
        fclose(fp);
        rackfiles[n_rackfiles].nActionSets = nActionSet;
        rackfiles[n_rackfiles].actionSets[ max( nActionSet - 1, 0 ) ].nActions = nAction;
        n_rackfiles++;
    }
}


/**
 * @brief   Store all files ( not directories ) in specified directory
 *          for later analysis
 * 
 * @param ignorefile    files to not store
 * @param dirname       store files at specified filepath
 */
void list_directory(char *ignorefile, char *dirname)
{
    DIR *dirp = opendir(dirname);
    struct dirent   *dp;

    if (dirp != NULL) 
    {
        int ind = 0;
        while ((dp = readdir(dirp)) != NULL) 
        {  
            if (dp->d_type != DT_DIR && !strstr(dp->d_name, ignorefile))
            // if (!strstr(dp->d_name, ".") && !strstr(dp->d_name, "..") && !strstr(dp->d_name, ignorefile))
            {
                printf(" - %s\n", dp->d_name );
                files_in_dir[ind++] = dp->d_name;
                n_files_in_dir++;
            }
        }
        closedir(dirp);
    }
}


int main(int argc, char *argv[])
{
    printf("\n");

    // DO NOT EXAMINE PROGRAM FILE IF IN SEARCH DIRECTORY
    char *progname = argv[0];
    progname += 2;

    printf(CYN);

    // READ FROM CURRENT DIRECTORY
    if (argc == 1)
    {
        printf("Found files at current directory:\n");
        list_directory(progname, ".");
    }

    // READ FROM SPECIFIED DIRECTORY ( FROM COMMAND LINE ARGS )
    else if (argc > 1)
    {
        printf("Found files at %s:\n", argv[1]);
        list_directory(progname, argv[1]);
    }

    printf(RESET); printf("\n");

    // EXTRACT INFO FROM EACH FILE
    for (int i=0 ; i<n_files_in_dir ; i++)
        parse_file(files_in_dir[i]);

    // DEBUGGING
    printf(YEL);
    read_rackfile();
    printf(RESET);

    printf("\n");
    return EXIT_SUCCESS;
}

// cc -std=c99 -Wall -Werror -o client-c client-c.c && ./client-c
