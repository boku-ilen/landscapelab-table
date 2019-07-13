import cv2 as cv
import socket
import threading
import numpy as np
from functools import partial

IMAGE_PATH = 'E:/Users/rotzr/Documents/Desktoperweiterungen/desktop/Arbeit/BOKU_2018/TestProjekte/QGIS_Remote/outputImage.png'
# TODO read image path from config file

# TODO define extent via lego-client
#      rewrite the render_image function in QGIS_UTILITY_FUNCTIONS so that it does not rely on the canvas anymore
#      and let the lego client directly request a rendered image for a given extent
#      this would circumvent the need for the PowerPan plugin and solve current visualisation issues in QGIS
#      it would also probably make it possible to run QGIS headless


# NOTE one loading and one saving cycle may hamper performance

# TODO logging instead of print even in prototypes

class StopCVControllerException(Exception):
    pass


class CVController(threading.Thread):

    def __init__(self, sock: socket, addr: (str, int)):
        threading.Thread.__init__(self)
        self.qgis_image = [
            np.zeros((500, 500, 3), np.uint8),
            np.zeros((500, 500, 3), np.uint8)
        ]
        self.current_image = 0
        self.sock = sock
        self.addr = addr

        self.button_map = {
            ord('w'): partial(self.send, b'pan_up'),
            ord('s'): partial(self.send, b'pan_down'),
            ord('a'): partial(self.send, b'pan_left'),
            ord('d'): partial(self.send, b'pan_right'),
            ord('q'): partial(self.send, b'zoom_in'),
            ord('e'): partial(self.send, b'zoom_out'),
            ord('x'): partial(self.quit)
        }

    # reloads the viewport image
    def refresh(self):
        unused_slot = (self.current_image + 1) % 2

        self.qgis_image[unused_slot] = cv.imread(IMAGE_PATH, 0)
        self.current_image = unused_slot

    # registers keyboard input and displays the current image
    def run(self):

        print("starting display session")
        cv.namedWindow("Display", cv.WINDOW_AUTOSIZE)
        try:
            while True:
                cv.imshow("Display", self.qgis_image[self.current_image])

                k = cv.waitKey(6)

                if k in self.button_map:
                    self.button_map[k]()

        except StopCVControllerException:
            # nothing to do here... just let the thread finish
            pass

        finally:
            cv.destroyAllWindows()
            self.sock.close()

    # sends a message to qgis
    def send(self, msg: bytes):
        print('sending: {}'.format(msg))
        self.sock.sendto(msg, self.addr)

    # sends a message to exit and then proceeds to quit out of the thread
    def quit(self):
        self.sock.sendto(b'exit', self.addr)
        # TODO find a way to kill listener thread with this... relying on QGIS to respond with exit is bad practice
        raise StopCVControllerException()
