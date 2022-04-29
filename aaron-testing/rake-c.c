#include <stdio.h>
#include <stdlib.h>

#include  <string.h>
#include  <sys/types.h>
#include  <dirent.h>

#define     MAX_FILES_IN_DIRECTORY      128
#define     MAX_FILES_TO_PROCESS        128
#define     BUFFER_SIZE                 512
#define     MAX_FILE_NAME               64

#define     RED                         "\e[0;31m"
#define     GRN                         "\e[0;32m"
#define     YEL                         "\e[0;33m"
#define     BLU                         "\e[0;34m"
#define     MAG                         "\e[0;35m"
#define     CYN                         "\e[0;36m"
#define     WHT                         "\e[0;37m"
#define     RESET                       "\e[0m"

typedef struct ActionSets {
    char    actions[BUFFER_SIZE];
    char    dependencies[BUFFER_SIZE];
} ActionSets;

typedef struct Rackfile
{
    int     port;
    char    hosts[BUFFER_SIZE];

    char    ActionSets[BUFFER_SIZE];   //  each VALID line
} Rackfile;


int n_files_in_dir;
char *files_in_dir[MAX_FILES_TO_PROCESS];


void read_file(char *filename)
{
    FILE  *fp;
    char  line[BUFFER_SIZE];

    fp       = fopen(filename, "r");
    if(fp != NULL) 
    {
        while(fgets(line, sizeof(line), fp) != NULL) 
        {
            printf("%s", line);
        }
    }
    fclose(fp);
}


void list_directory(char *ignorefile, char *dirname)
{
    printf(CYN);

    // char files_to_ignore[MAX_FILE_NAME][MAX_FILES_IN_DIRECTORY];
    // files_to_ignore[0] = ".";
    // files_to_ignore[0] = "..";

    DIR             *dirp;
    struct dirent   *dp;

    dirp       = opendir(dirname);
    if(dirp != NULL) 
    {
        int ind = 0;
        while((dp = readdir(dirp)) != NULL) 
        {  
            if(dp->d_type != DT_DIR && !strstr(dp->d_name, ignorefile))
            {
                printf( "%s\n", dp->d_name );
                files_in_dir[ind++] = dp->d_name;
                n_files_in_dir++;
            }
        }
        closedir(dirp);
    }

    printf(RESET);
}

int main(int argc, char *argv[])
{
    printf("\n");

    n_files_in_dir = 0;

    char *progname = argv[0];
    progname += 2;

    // READ FROM CURRENT DIRECTORY
    if (argc == 1)
        list_directory(progname, ".");

    // READ FROM CURRENT DIRECTORY
    else if (argc > 1)
        list_directory(progname, argv[1]);

    printf("\n");

    for (int i=0 ; i<n_files_in_dir ; i++)
    {
        printf("%i. %s\n", i, files_in_dir[i]);
        printf(MAG);
        read_file(files_in_dir[i]);
        printf(RESET);
        printf("\n");
    }



    printf("\n");
    return EXIT_SUCCESS;
}

// cc -std=c99 -Wall -Werror -pedantic -o