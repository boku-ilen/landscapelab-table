import socket
import logging
import threading
from typing import Dict

from .MapHandler import MapHandler
from ..Configurator import Configurator
from LabTable.Model.Extent import Extent

# Configure logger
logger = logging.getLogger(__name__)


# ListenerThread class
# used for communication with QGIS-plugin
# relies on map handler to send closing message
class QGISListenerThread(threading.Thread):

    running = False

    def __init__(self, config: Configurator, map_dict: Dict[str, MapHandler]):

        # call super()
        threading.Thread.__init__(self)
        self.name = "[LabTable] QGIS Listener"

        # create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((config.get('qgis_interaction', 'qgis_ip'), config.get('qgis_interaction', 'table_read_port')))
        self.udp_buffer_size = config.get('qgis_interaction', 'udp_buffer_size')

        # remember update keyword
        self.update_keyword = config.get('qgis_interaction', 'update_keyword')
        self.exit_keyword = config.get('qgis_interaction', 'exit_keyword')

        self.map_dict = map_dict

    # waits for messages from qgis plugin and notifies map objects in case they should be updated
    def run(self):

        logger.info("starting to listen for qgis messages")
        self.running = True
        while self.running:
            data, addr = self.sock.recvfrom(1024)

            data = data.decode()
            logger.info(data)
            if data.startswith(self.update_keyword):

                # convert extent to numpy array
                info = data[len(self.update_keyword):]
                info = info.split(' ')
                target_name = info[0]
                extent = info[1:5]
                extent = Extent(float(extent[0]), float(extent[1]), float(extent[2]), float(extent[3]), True)

                if target_name in self.map_dict:
                    self.map_dict[target_name].refresh(extent)

            if data == self.exit_keyword:
                self.close()

    def close(self):
        logger.info("shutting down QGIS Listener")
        self.sock.close()
        self.running = False
