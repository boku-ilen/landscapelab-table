import socket
from CVControllerThread import CVControllerThread
from ListenerThread import ListenerThread
import LegoDetection.config as config


def main():

    # create sockets
    read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    read_socket.bind((config.QGIS_IP, config.LEGO_READ_PORT))
    write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    write_target = (config.QGIS_IP, config.QGIS_READ_PORT)

    # create and start the threads
    cv_c = CVControllerThread(write_socket, write_target)
    listener = ListenerThread(read_socket, config.UDP_BUFFER_SIZE, cv_c)

    # starting
    cv_c.start()
    listener.start()

    # wait till all threads are finished, then close the socket
    cv_c.join()
    listener.join()


if __name__ == '__main__':
    main()
