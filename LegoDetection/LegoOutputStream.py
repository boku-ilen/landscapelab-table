from enum import Enum

import cv2
from ConfigManager import ConfigManager
from LegoUI.MapHandler import MapHandler
from functools import partial
from LegoUI.MapActions import MapActions
from LegoUI.UIElements.UIElement import UIElement, MOUSE_BRICKS, MOUSE_BRICK_SIZE
from LegoBricks import LegoBrick, LegoColor, LegoShape
import numpy as np
import logging


# enable logger

logger = logging.getLogger(__name__)

BRICK_LABEL_OFFSET = 10


class LegoOutputChannel(Enum):

    CHANNEL_SHAPE_DETECTION = 1
    CHANNEL_BOARD_DETECTION = 2
    CHANNEL_ROI = 3
    CHANNEL_COLOR = 4
    CHANNEL_CLIPPED_COLOR = 5
    CHANNEL_WHITE_BLACK = 6

    def next(self):
        value = self.value + 1
        if value > 6:
            value = 6
        return LegoOutputChannel(value)

    def prev(self):
        value = self.value - 1
        if value < 1:
            value = 1
        return LegoOutputChannel(value)


# this class handles the output video streams
class LegoOutputStream:

    WINDOW_NAME_DEBUG = 'DEBUG WINDOW'
    WINDOW_NAME_BEAMER = 'BEAMER WINDOW'

    def __init__(self, map_handler: MapHandler, ui_root: UIElement, config: ConfigManager, video_output_name=None):

        self.active_channel = LegoOutputChannel.CHANNEL_COLOR
        self.active_window = LegoOutputStream.WINDOW_NAME_DEBUG  # TODO: implement window handling

        # create output windows
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_DEBUG, cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_BEAMER, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(LegoOutputStream.WINDOW_NAME_BEAMER, LegoOutputStream.beamer_mouse_callback)

        if video_output_name:
            # Define the codec and create VideoWriter object. The output is stored in .avi file.
            # Define the fps to be equal to 10. Also frame size is passed.
            self.video_handler = cv2.VideoWriter(
                video_output_name,
                cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                10,
                (config.get('resolution', 'width'), config.get('resolution', 'height'))
            )
        else:
            self.video_handler = None

        # set ui_root and map handler
        self.ui_root = ui_root
        self.map_handler = map_handler

        # setup button map
        # reads corresponding keyboard input for action with config.get(...) and converts it to int with ord(...)
        self.BUTTON_MAP = {
            ord(config.get('button_map', 'DEBUG_CHANNEL_UP')): self.channel_up,
            ord(config.get('button_map', 'DEBUG_CHANNEL_DOWN')): self.channel_down,
            ord(config.get('button_map', 'MAP_PAN_UP')): partial(map_handler.invoke, MapActions.PAN_UP),
            ord(config.get('button_map', 'MAP_PAN_DOWN')): partial(map_handler.invoke, MapActions.PAN_DOWN),
            ord(config.get('button_map', 'MAP_PAN_LEFT')): partial(map_handler.invoke, MapActions.PAN_LEFT),
            ord(config.get('button_map', 'MAP_PAN_RIGHT')): partial(map_handler.invoke, MapActions.PAN_RIGHT),
            ord(config.get('button_map', 'MAP_ZOOM_IN')): partial(map_handler.invoke, MapActions.ZOOM_IN),
            ord(config.get('button_map', 'MAP_ZOOM_OUT')): partial(map_handler.invoke, MapActions.ZOOM_OUT)
        }

    # Write the frame into the file
    def write_to_file(self, frame):
        # TODO: shouldn't we be able to select which channel we want to write to the file?
        if self.video_handler:
            self.video_handler.write(frame)

    # write the frame into a window
    def write_to_channel(self, channel, frame):
        # TODO: currently everything not written to the active channel is dropped
        if channel == self.active_channel:
            cv2.imshow(self.active_window, frame)

    # change the active channel, which is displayed in the window
    def set_active_channel(self, channel):
        self.active_channel = channel

    def channel_up(self):
        logger.info("changed active channel one up")
        self.set_active_channel(self.active_channel.next())

    def channel_down(self):
        logger.info("changed active channel one down")
        self.set_active_channel(self.active_channel.prev())

    # mark the candidate in given frame
    @staticmethod
    def mark_candidates(frame, candidate_contour):
        cv2.drawContours(frame, [candidate_contour], -1, (255, 0, 0), 3)

    # we label the identified lego bricks in the stream
    @staticmethod
    def labeling(frame, tracked_lego_brick: LegoBrick):

        # FIXME: extract constants! and change array  [][] access into named attribute access
        # Draw lego bricks IDs
        text = "ID {}".format(tracked_lego_brick.asset_id)
        tracked_lego_brick_position = tracked_lego_brick.centroid_x, tracked_lego_brick.centroid_y
        cv2.putText(frame, text, (tracked_lego_brick.centroid_x - BRICK_LABEL_OFFSET,
                                  tracked_lego_brick.centroid_y - BRICK_LABEL_OFFSET),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

        # Draw lego bricks contour names
        # FIXME: put other caption like id of the lego brick
        cv2.putText(frame, tracked_lego_brick.status.name, tracked_lego_brick_position,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

        # Draw lego bricks centroid points
        cv2.circle(frame, tracked_lego_brick_position, 4, (0, 255, 0), -1)

    def update(self) -> bool:

        self.redraw_beamer_image()

        key = cv2.waitKeyEx(1)

        if key in self.BUTTON_MAP:
            self.BUTTON_MAP[key]()

        # Break with Esc  # FIXME: CG: keyboard might not be available - use signals?
        if key == 27:
            return True
        else:
            return False

    # redraws
    def redraw_beamer_image(self):

        if MapHandler.MAP_REFRESHED or UIElement.UI_REFRESHED:
            frame = self.map_handler.get_frame()
            self.ui_root.draw(frame)
            # render all mouse placed bricks
            for brick in MOUSE_BRICKS:
                pos = np.array((brick.centroid_x, brick.centroid_y))
                half_size = np.array((MOUSE_BRICK_SIZE, MOUSE_BRICK_SIZE))
                cv2.rectangle(frame, tuple(pos - half_size), tuple(pos + half_size), (0, 255, 0), cv2.FILLED)

            cv2.imshow(LegoOutputStream.WINDOW_NAME_BEAMER, frame)

            MapHandler.MAP_REFRESHED = False
            UIElement.UI_REFRESHED = False

    # closing the outputstream if it is defined
    def close(self):
        cv2.destroyAllWindows()
        if self.video_handler:
            self.video_handler.release()

    @staticmethod
    def beamer_mouse_callback(event, x, y, flags, param):
        mouse_pos = np.array((x, y))
        UIElement.UI_REFRESHED = True

        if event == cv2.EVENT_LBUTTONDOWN or event == cv2.EVENT_RBUTTONDOWN:
            for brick in MOUSE_BRICKS:
                pos = np.array((brick.centroid_x, brick.centroid_y))

                # if mouse is in radius 5 to the brick remove it and stop
                if np.linalg.norm(pos - mouse_pos) < MOUSE_BRICK_SIZE:
                    MOUSE_BRICKS.remove(brick)

                    logging.info('removed brick')
                    logging.info('{} bricks remaining'.format(len(MOUSE_BRICKS)))
                    return

            # if mouse is on no brick create a new one
            brick = LegoBrick(x, y, LegoShape.SQUARE_BRICK, LegoColor.BLUE_BRICK)
            MOUSE_BRICKS.append(brick)

            logging.info('added brick at {}'.format(mouse_pos))
            logging.info('{} bricks on map'.format(len(MOUSE_BRICKS)))
