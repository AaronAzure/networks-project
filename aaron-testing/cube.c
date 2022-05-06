#include <stdio.h>
#include <stdlib.h>

int cube(int x)
{
    return x * x * x;
}

int main(int argc, char *argv[])
{
    if (argc != 2)
        exit(EXIT_FAILURE);
    
    int value = cube( atoi(argv[1]) );
    
    exit(EXIT_SUCCESS);
}