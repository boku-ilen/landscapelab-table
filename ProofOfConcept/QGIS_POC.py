# NOTE since this script is executed in the QGIS-Python environment
#  PyCharm might wrongfully mark some libraries/classes as unknown
import os
from powerpan.power_pan_dockwidget import PowerPanDockWidget
from qgis.core import *
from qgis.utils import *
from functools import partial
import socket
import numpy as np
from QGIS_UTILITY_FUNCTIONS import render_image


"""
NOTE: in order for this script to work, the QGIS plugin PowerPan has to be installed

To run this make sure that the path to this file is included in sys.path
then call 'import QGIS_POC1' in the QGIS pyton console
"""

# setup UDP socket config
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
UDP_BUFFER_SIZE = 1024
# TODO read from config file

# define how much percent of the previous map-viewport should still be visible after panning in one direction
PAN_JUMP_SIZE = 80

RENDER_KEYWORD = 'render '


class RemoteRendering(QgsTask):

    def __init__(self):
        super().__init__('remote control listener task', QgsTask.CanCancel)

        # define image path
        self.image_location = os.path.join(QgsProject.instance().homePath(), 'outputImage.png')

        # setup UDP socket
        self.read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.read_socket.bind((UDP_IP, UDP_PORT))
        self.write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.write_target = (UDP_IP, UDP_PORT + 1)

        # set canvas
        self.canvas = iface.mapCanvas()

        # every time the map has finished rendering call save_image()
        self.canvas.mapCanvasRefreshed.connect(partial(self.keep_task_alive))
        # TODO  ^
        #       |   Yes, Officer, this line right here!!
        #       |   If there was a king of bad smell, this line would probably be it
        #       |   I don't know why, but when this line gets removed, the Task does not show up in the Task list
        #       |   This might have to do with garbage collection? Since the Task is stored nowhere else?
        #       |   Just a guess though...

    # listens on socket for commands and
    def run(self):

        try:
            QgsMessageLog.logMessage('starting to listen for messages')
            while True:
                # wait for msg
                data, addr = self.read_socket.recvfrom(UDP_BUFFER_SIZE)
                QgsMessageLog.logMessage('got message {} from address {}'.format(data, addr))

                decoded_msg = data.decode()

                # if msg is exit stop
                if decoded_msg == 'exit':
                    self.write_socket.sendto(b'exit', self.write_target)
                    QgsMessageLog.logMessage('stop listening')
                    return True

                if decoded_msg.startswith(RENDER_KEYWORD):
                    extent_info = decoded_msg[len(RENDER_KEYWORD):]
                    extent = extent_info.split(' ')

                    extent = QgsRectangle(float(extent[0]), float(extent[1]), float(extent[2]), float(extent[3]))

                    render_image(extent, self.image_location)
                    self.write_socket.sendto(
                        'update {}'.format(extent_info).encode(),
                        self.write_target
                    )

        finally:
            self.read_socket.close()
            self.write_socket.close()

    def keep_task_alive(self):
        pass
        # TODO remove as soon as bad smell in __init__ is cleared


def start_remote_rendering_task():
    QgsApplication.taskManager().addTask(RemoteRendering())


start_remote_rendering_task()
