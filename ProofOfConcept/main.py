import socket
from CVController import CVController
from ListenerThread import ListenerThread


# setup UDP socket config
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
UDP_BUFFER_SIZE = 1024
# TODO: read from config file

# create socket
read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
read_socket.bind((UDP_IP, UDP_PORT+1))
write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def main():
    # create and start the threads
    cv_c = CVController(write_socket, (UDP_IP, UDP_PORT))
    listener = ListenerThread(read_socket, UDP_BUFFER_SIZE, cv_c)

    cv_c.start()
    listener.start()

    # wait till all threads are finished, then close the socket
    cv_c.join()
    listener.join()


if __name__ == '__main__':
    main()
