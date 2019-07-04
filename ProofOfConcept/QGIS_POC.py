import os
from powerpan.power_pan_dockwidget import PowerPanDockWidget
from qgis.core import *
from qgis.utils import *
from functools import partial
import socket

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


class Task(QgsTask):

    def __init__(self):
        super().__init__('remote control listener task', QgsTask.CanCancel)

        # define image path
        self.image_location = os.path.join(QgsProject.instance().homePath(), 'outputImage.png')

        # setup UDP socket
        self.read_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.read_socket.bind((UDP_IP, UDP_PORT))
        self.write_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # setup power pan plugin
        self.ppdw = PowerPanDockWidget(iface)
        # define how far the view should move when panning in one direction
        self.ppdw.txt_hoverlap.setText('{}'.format(PAN_JUMP_SIZE))
        self.ppdw.txt_voverlap.setText('{}'.format(PAN_JUMP_SIZE))

        # setup command_list
        command_list = {b'pan_up': [self.ppdw.btn_up_pressed, "panning up"],
                        b'pan_down': [self.ppdw.btn_down_pressed, "panning down"],
                        b'pan_left': [self.ppdw.btn_left_pressed, "panning left"],
                        b'pan_right': [self.ppdw.btn_right_pressed, "panning right"]}
        self.command_list = command_list

        # every time the map has finished rendering call save_image()
        self.canvas = iface.mapCanvas()
        self.canvas.mapCanvasRefreshed.connect(partial(self.save_image))

    # listens on socket for commands and
    def run(self):

        try:
            while True:
                # wait for msg
                data, addr = self.read_socket.recvfrom(UDP_BUFFER_SIZE)
                QgsMessageLog.logMessage('got message {} from address {}'.format(data, addr))

                # if msg is exit stop
                if data == b'exit':
                    self.write_socket.sendto(b'exit', (UDP_IP, UDP_PORT + 1))
                    QgsMessageLog.logMessage('stop listening')
                    return True

                # else try executing the command
                self.act(data)

        finally:
            self.read_socket.close()

    # check if command is known and execute it
    def act(self, command: bytes):
        
        if command in self.command_list:
            self.command_list[command][0]()
            QgsMessageLog.logMessage(self.command_list[command][1])

    # saves the current viewport to an image
    # then notifies lego client to update
    def save_image(self):

        self.canvas.saveAsImage(self.image_location, None, "PNG")
        self.write_socket.sendto(b'update', (UDP_IP, UDP_PORT + 1))
        # TODO include corner positions in update message

QgsApplication.taskManager().addTask(Task())
