import socket
import numpy as np
from CVControllerThread import CVControllerThread
from ListenerThread import ListenerThread

# setup UDP socket config
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
UDP_BUFFER_SIZE = 1024
# TODO: read from config file

start_extent = np.array([
    112518.16800000000512227, 275472.02100000000791624,
    685444.46299999998882413, 570431.06900000001769513
])
# TODO read from config / server

# create socket
read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
read_socket.bind((UDP_IP, UDP_PORT+1))
write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def main():
    # create and start the threads
    cv_c = CVControllerThread(write_socket, (UDP_IP, UDP_PORT), start_extent)
    listener = ListenerThread(read_socket, UDP_BUFFER_SIZE, cv_c)

    # starting
    cv_c.start()
    listener.start()

    # wait till all threads are finished, then close the socket
    cv_c.join()
    listener.join()


if __name__ == '__main__':
    main()
