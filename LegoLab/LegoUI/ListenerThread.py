import socket
import logging
import threading
from typing import Dict

from LegoUI.MapHandler import MapHandler
from ConfigManager import ConfigManager
from LegoExtent import LegoExtent

# Configure logger
logger = logging.getLogger(__name__)


class ListenerThread(threading.Thread):

    def __init__(self, config: ConfigManager, map_dict: Dict[str, MapHandler]):
        threading.Thread.__init__(self)

        # create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((config.get('qgis_interaction', 'QGIS_IP'), config.get('qgis_interaction', 'LEGO_READ_PORT')))
        self.udp_buffer_size = config.get('qgis_interaction', 'UDP_BUFFER_SIZE')

        # remember update keyword
        self.update_keyword = config.get('qgis_interaction', 'UPDATE_KEYWORD')
        self.exit_keyword = config.get('qgis_interaction', 'EXIT_KEYWORD')

        self.map_dict = map_dict

    def run(self):
        logger.info("starting to listen for messages")
        while True:
            data, addr = self.sock.recvfrom(1024)

            data = data.decode()
            logger.info(data)
            if data.startswith(self.update_keyword):

                # convert extent to numpy array
                info = data[len(self.update_keyword):]
                info = info.split(' ')
                target_name = info[0]
                extent = info[1:5]
                extent = LegoExtent(float(extent[0]), float(extent[1]), float(extent[2]), float(extent[3]), True)

                if target_name in self.map_dict:
                    self.map_dict[target_name].refresh(extent)

            if data == self.exit_keyword:
                self.sock.close()
                break
