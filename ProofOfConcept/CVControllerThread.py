import cv2 as cv
import socket
import threading
import numpy as np
from functools import partial

IMAGE_PATH = 'E:/Users/rotzr/Documents/Desktoperweiterungen/desktop/Arbeit/BOKU_2018/TestProjekte/QGIS_Remote/outputImage.png'
# TODO read image path from config file

# NOTE one loading and one saving cycle may hamper performance

# TODO logging instead of print even in prototypes

class StopCVControllerException(Exception):
    pass


class CVControllerThread(threading.Thread):

    def __init__(self, sock: socket, addr: (str, int), start_extent):
        threading.Thread.__init__(self)

        # initialize two black images
        self.qgis_image = [
            np.zeros((500, 500, 3), np.uint8),
            np.zeros((500, 500, 3), np.uint8)
        ]
        self.current_image = 0

        # set extents
        self.current_extent = start_extent
        self.next_extent = start_extent

        # set socket info
        self.sock = sock
        self.addr = addr

        # set extent modifiers
        pan_power = 0.1
        zoom_power = 0.2
        # TODO read from config
        pan_up_modifier = np.array([0, 1, 0, 1])
        pan_down_modifier = np.array([0, -1, 0, -1])
        pan_left_modifier = np.array([-1, 0, -1, 0])
        pan_right_modifier = np.array([1, 0, 1, 0])
        zoom_in_modifier = np.array([1, 1, -1, -1])
        zoom_out_modifier = np.array([-1, -1, 1, 1])

        # set up button map
        self.button_map = {
            ord('w'): partial(self.init_render, pan_up_modifier, pan_power),
            ord('s'): partial(self.init_render, pan_down_modifier, pan_power),
            ord('a'): partial(self.init_render, pan_left_modifier, pan_power),
            ord('d'): partial(self.init_render, pan_right_modifier, pan_power),
            ord('q'): partial(self.init_render, zoom_in_modifier, zoom_power),
            ord('e'): partial(self.init_render, zoom_out_modifier, zoom_power),
            ord('x'): partial(self.quit)
        }

    # reloads the viewport image
    def refresh(self, extent):
        unused_slot = (self.current_image + 1) % 2

        self.qgis_image[unused_slot] = cv.imread(IMAGE_PATH, 0)
        self.current_image = unused_slot
        self.current_extent = extent

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

    # modifies the current extent and requests an updated render image
    def init_render(self, extent_modifier, strength):

        # modify extent
        width = abs(self.current_extent[2] - self.current_extent[0])
        height = abs(self.current_extent[3] - self.current_extent[1])

        move_extent = np.multiply(
            extent_modifier,
            np.array([width, height, width, height])
        ) * strength

        next_extent = np.add(self.current_extent, move_extent)

        # request render
        self.send(
            'render {} {} {} {}'.format(next_extent[0], next_extent[1], next_extent[2], next_extent[3])
            .encode()
        )

    # sends a message to qgis
    def send(self, msg: bytes):
        print('sending: {}'.format(msg))
        self.sock.sendto(msg, self.addr)

    # sends a message to exit and then proceeds to quit out of the thread
    def quit(self):
        self.sock.sendto(b'exit', self.addr)
        # TODO find a way to kill listener thread with this... relying on QGIS to respond with exit is bad practice
        raise StopCVControllerException()
