import sys

# port number
port_num = 12345

# total arguments
n_args = len(sys.argv)
# print(n_args)

# Using argparse module
if n_args > 1:
    port_num = int(sys.argv[1])


def main():
    print("listening on port=" + str(port_num) + ", sd=")
    

main()



