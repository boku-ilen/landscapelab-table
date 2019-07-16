import socket
import logging
import threading
import numpy as np
import LegoDetection.config as config
from CVControllerThread import CVControllerThread

# Configure logger
logger = logging.getLogger(__name__)


class ListenerThread(threading.Thread):

    def __init__(self, sock: socket, udp_buffer_size, cv_controller: CVControllerThread):
        threading.Thread.__init__(self)

        self.sock = sock
        self.udp_buffer_size = udp_buffer_size

        self.cv_controller = cv_controller

    def run(self):
        logger.info("starting to listen for messages")
        while True:
            data, addr = self.sock.recvfrom(1024)

            data = data.decode()
            logger.debug(data)
            if data.startswith(config.UPDATE_KEYWORD):

                # convert extent to numpy array
                extent_info = data[len(config.UPDATE_KEYWORD):]
                extent = extent_info.split(' ')
                extent = np.array([float(extent[0]), float(extent[1]), float(extent[2]), float(extent[3])])

                self.cv_controller.refresh(extent)

            if data == 'exit':     # todo ctrl-c capturen
                self.sock.close()
                break
