import cv2 as cv
import socket
import threading
import numpy as np
from functools import partial
import LegoDetection.config as config
from LegoDetection.Tracking.LegoBrick import LegoBrick, LegoStatus, LegoShape, LegoColor
from LegoUI.UIElements.UISetup import setup_ui
from LegoUI.MapActions import MapActions
from typing import List
import logging

# NOTE one loading and one saving cycle may hamper performance

# Configure Logger
logger = logging.getLogger(__name__)

lego_bricks: List[LegoBrick] = []
SIM_BRICK_SIZE = 10


class StopCVControllerException(Exception):
    pass


class CVControllerThread(threading.Thread):

    def __init__(self, sock: socket, qgis_addr: (str, int), lego_addr: (str,int)):
        threading.Thread.__init__(self)

        # initialize two black images
        self.qgis_image = [
            np.zeros((500, 500, 3), np.uint8),
            np.zeros((500, 500, 3), np.uint8)
        ]
        self.current_image = 0

        # set extents
        self.current_extent = config.start_extent
        self.next_extent = config.start_extent

        # set socket info
        self.sock = sock
        self.qgis_addr = qgis_addr
        self.lego_addr = lego_addr

        # request first render
        self.request_render(self.current_extent)

        # set extent modifiers
        pan_up_modifier = np.array([0, 1, 0, 1])
        pan_down_modifier = np.array([0, -1, 0, -1])
        pan_left_modifier = np.array([-1, 0, -1, 0])
        pan_right_modifier = np.array([1, 0, 1, 0])
        zoom_in_modifier = np.array([1, 1, -1, -1])
        zoom_out_modifier = np.array([-1, -1, 1, 1])

        # set up button map
        self.button_map = {
            ord('w'): MapActions.PAN_UP,
            ord('s'): MapActions.PAN_DOWN,
            ord('a'): MapActions.PAN_LEFT,
            ord('d'): MapActions.PAN_RIGHT,
            ord('q'): MapActions.ZOOM_IN,
            ord('e'): MapActions.ZOOM_OUT,
            ord('x'): MapActions.QUIT,
        }

        self.action_map = {
            MapActions.PAN_UP: partial(self.init_render, pan_up_modifier, config.PAN_DISTANCE),
            MapActions.PAN_DOWN: partial(self.init_render, pan_down_modifier, config.PAN_DISTANCE),
            MapActions.PAN_LEFT: partial(self.init_render, pan_left_modifier, config.PAN_DISTANCE),
            MapActions.PAN_RIGHT: partial(self.init_render, pan_right_modifier, config.PAN_DISTANCE),
            MapActions.ZOOM_IN: partial(self.init_render, zoom_in_modifier, config.ZOOM_STRENGTH),
            MapActions.ZOOM_OUT: partial(self.init_render, zoom_out_modifier, config.ZOOM_STRENGTH),
            MapActions.QUIT: partial(self.quit)
        }

        # setup ui
        self.ui_root = setup_ui(self.action_map)

    # reloads the viewport image
    def refresh(self, extent):
        unused_slot = (self.current_image + 1) % 2

        self.qgis_image[unused_slot] = cv.imread(config.QGIS_IMAGE_PATH, 1)
        self.current_image = unused_slot
        self.current_extent = extent

    # registers keyboard input and displays the current image
    def run(self):

        logger.info("starting display session")
        cv.namedWindow("Display", cv.WINDOW_AUTOSIZE)
        cv.setMouseCallback("Display", emulate_lego_brick)
        try:
            while True:
                frame = np.copy(self.qgis_image[self.current_image])

                # execute ui update logic
                for brick in lego_bricks:
                    self.ui_root.brick_on_element(brick)
                self.ui_root.finished_checking()

                # draw ui
                self.ui_root.draw(frame)

                # draw lego bricks
                for brick in lego_bricks:
                    pos = np.array((brick.centroid_x, brick.centroid_y))
                    half_size = np.array((SIM_BRICK_SIZE, SIM_BRICK_SIZE))
                    cv.rectangle(frame, tuple(pos - half_size), tuple(pos + half_size), (0, 255, 0), cv.FILLED)

                # draw to screen
                cv.imshow("Display", frame)

                k = cv.waitKey(6)

                if k in self.button_map:
                    self.action_map[self.button_map[k]](None)

        except StopCVControllerException:
            # nothing to do here... just let the thread finish
            pass

        finally:
            cv.destroyAllWindows()
            self.sock.close()

    # modifies the current extent and requests an updated render image
    # param brick gets ignored so that UIElements can call the function
    def init_render(self, extent_modifier, strength, brick):

        # modify extent
        width = abs(self.current_extent[2] - self.current_extent[0])
        height = abs(self.current_extent[3] - self.current_extent[1])

        move_extent = np.multiply(
            extent_modifier,
            np.array([width, height, width, height])
        ) * strength

        next_extent = np.add(self.current_extent, move_extent)

        # request render
        self.request_render(next_extent)

    def request_render(self, extent):
        self.send(
            '{}{} {} {} {}'.format(config.RENDER_KEYWORD, extent[0], extent[1], extent[2], extent[3])
            .encode()
        )

    # sends a message to qgis
    def send(self, msg: bytes):
        logger.debug('sending: {}'.format(msg))
        self.sock.sendto(msg, self.qgis_addr)

    # determines if a given lego brick is placed on an UI element (internal brick) or not (external brick)
    # also calls UI callback functions if brick is internal
    def classify_brick_type(self, brick: LegoBrick):
        # TODO implement interface
        pass

    # sends a message to exit and then proceeds to quit out of the thread
    # param brick gets ignored, this exists so that the UI can use this function
    def quit(self, brick):
        self.sock.sendto(b'exit', self.qgis_addr)
        self.sock.sendto(b'exit', self.lego_addr)
        raise StopCVControllerException()


# openCV callback function that emulates
def emulate_lego_brick(event, x, y, flags, param):

    mouse_pos = np.array((x, y))

    if event == cv.EVENT_LBUTTONDOWN or event == cv.EVENT_RBUTTONDOWN:
        for brick in lego_bricks:
            pos = np.array((brick.centroid_x, brick.centroid_y))

            # if mouse is in radius 5 to the brick remove it and stop
            if np.linalg.norm(pos - mouse_pos) < SIM_BRICK_SIZE:
                lego_bricks.remove(brick)
                logging.info('removed brick')
                logging.info('{} bricks remaining'.format(len(lego_bricks)))
                return

        # if mouse is on no brick create a new one
        brick = LegoBrick(x, y, LegoShape.SQUARE_BRICK, LegoColor.BLUE_BRICK)
        lego_bricks.append(brick)

        logging.info('added brick at {}'.format(mouse_pos))
        logging.info('{} bricks on map'.format(len(lego_bricks)))
