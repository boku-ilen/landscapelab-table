import socket
import threading
from CVController import CVController


class ListenerThread(threading.Thread):

    def __init__(self, sock: socket, udp_buffer_size, cv_controller: CVController):
        threading.Thread.__init__(self)

        self.sock = sock
        self.udp_buffer_size = udp_buffer_size

        self.cv_controller = cv_controller

    def run(self):
        print("starting to listen for messages")
        while True:
            data, addr = self.sock.recvfrom(1024)

            print(data)
            if data == b'update':
                self.cv_controller.refresh()

            if data == b'exit':     # todo ctrl-c capturen
                self.sock.close()
                break
