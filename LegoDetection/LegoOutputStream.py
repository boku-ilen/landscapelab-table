from enum import Enum
import cv2
from Tracker import Tracker
from ConfigManager import ConfigManager
from LegoUI.MapHandler import MapHandler
from functools import partial
from typing import Callable, Tuple
from LegoUI.MapActions import MapActions
from LegoUI.UIElements.UIElement import UIElement
from LegoBricks import LegoBrick, LegoColor, LegoShape, LegoStatus
import numpy as np
import logging


# enable logger
logger = logging.getLogger(__name__)

# drawing constants
BRICK_DISPLAY_SIZE = 10
VIRTUAL_BRICK_ALPHA = 0.7
BRICK_LABEL_OFFSET = 10
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
FONT_SIZE = 0.4
FONT_THICKNESS = 1
CONTOUR_THICKNESS = 3
IDX_DRAW_ALL = -1
RADIUS = 3


class LegoOutputChannel(Enum):

    CHANNEL_COLOR_DETECTION = 1
    CHANNEL_MASKS = 2
    CHANNEL_WHITE_BLACK = 3

    def next(self):
        value = self.value + 1
        if value > 3:
            value = 3
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

    MOUSE_BRICKS_REFRESHED = False

    def __init__(self,
                 map_handler: MapHandler,
                 ui_root: UIElement,
                 tracker: Tracker,
                 config: ConfigManager,
                 video_output_name=None):

        self.config = config

        self.active_channel = LegoOutputChannel.CHANNEL_COLOR_DETECTION
        self.active_window = LegoOutputStream.WINDOW_NAME_DEBUG  # TODO: implement window handling

        # create output windows
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_DEBUG, cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_BEAMER, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(LegoOutputStream.WINDOW_NAME_BEAMER, self.beamer_mouse_callback)

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

        self.last_frame = None

        # create conversion methods
        self.board_to_beamer = partial(LegoOutputStream.remap_brick, self.get_board_res, self.get_beamer_res)
        self.beamer_to_board = partial(LegoOutputStream.remap_brick, self.get_beamer_res, self.get_board_res)

        # set ui_root and map handler, create empty variable for tracker
        self.ui_root = ui_root
        self.map_handler = map_handler
        self.tracker: Tracker = tracker
        self.tracker.get_board_to_beamer_conversion = lambda: self.board_to_beamer

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
        cv2.drawContours(frame, [candidate_contour], IDX_DRAW_ALL, BLUE, CONTOUR_THICKNESS)

    # we label the identified lego bricks in the stream
    @staticmethod
    def labeling(frame, tracked_lego_brick: LegoBrick):

        # Draw lego bricks IDs
        text = "ID {}".format(tracked_lego_brick.asset_id)
        tracked_lego_brick_position = tracked_lego_brick.centroid_x, tracked_lego_brick.centroid_y
        cv2.putText(frame, text, (tracked_lego_brick.centroid_x - BRICK_LABEL_OFFSET,
                                  tracked_lego_brick.centroid_y - BRICK_LABEL_OFFSET),
                    cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, BLUE, FONT_THICKNESS)

        # Draw lego bricks contour names
        # FIXME: put other caption like id of the lego brick
        cv2.putText(frame, tracked_lego_brick.status.name, tracked_lego_brick_position,
                    cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, BLUE, FONT_THICKNESS)

        # Draw lego bricks centroid points
        cv2.circle(frame, tracked_lego_brick_position, RADIUS, GREEN, cv2.FILLED)

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

    # redraws the beamer image
    def redraw_beamer_image(self):

        if MapHandler.MAP_REFRESHED \
                or UIElement.UI_REFRESHED \
                or Tracker.BRICKS_REFRESHED \
                or LegoOutputStream.MOUSE_BRICKS_REFRESHED:
            frame = self.map_handler.get_frame().copy()

            # render virtual external bricks behind ui
            self.render_external_virtual_bricks(frame)

            # render ui
            self.ui_root.draw(frame)

            # render remaining bricks in front of ui
            self.render_bricks(frame)

            cv2.imshow(LegoOutputStream.WINDOW_NAME_BEAMER, frame)
            self.last_frame = frame

            MapHandler.MAP_REFRESHED = False
            UIElement.UI_REFRESHED = False

    # renders only external virtual bricks since they should be displayed behind the ui unlike any other brick types
    def render_external_virtual_bricks(self, render_target):

        overlay_target = np.zeros_like(render_target)
        for brick in filter(lambda b: b.status == LegoStatus.EXTERNAL_BRICK, self.tracker.virtual_bricks):
            self.render_brick(brick, overlay_target)
        cv2.addWeighted(overlay_target, VIRTUAL_BRICK_ALPHA, render_target, 1, 0, render_target)

    # renders all bricks except external virtual ones since those get rendered earlier
    def render_bricks(self, render_target):
        # render all confirmed bricks
        for brick in self.tracker.confirmed_bricks:
            self.render_brick(brick, render_target)

        # render virtual bricks
        overlay_target = np.zeros_like(render_target)
        for brick in list(filter(lambda b: b.status != LegoStatus.EXTERNAL_BRICK, self.tracker.virtual_bricks)):
            self.render_brick(brick, overlay_target)
        cv2.addWeighted(overlay_target, VIRTUAL_BRICK_ALPHA, render_target, 1, 0, render_target)

    def render_brick(self, brick, render_target):
        b = self.board_to_beamer(brick)
        pos = np.array((b.centroid_x, b.centroid_y))
        half_size = np.array((BRICK_DISPLAY_SIZE, BRICK_DISPLAY_SIZE))

        color = GREEN
        if b.status == LegoStatus.OUTDATED_BRICK:
            color = RED
        elif b.status == LegoStatus.EXTERNAL_BRICK:
            color = BLUE

        cv2.rectangle(render_target, tuple(pos - half_size), tuple(pos + half_size), color, cv2.FILLED)

    # closing the outputstream if it is defined
    def close(self):
        cv2.destroyAllWindows()
        if self.video_handler:
            self.video_handler.release()

    @staticmethod
    def remap_brick(source_res: Callable[[], Tuple[int, int]],
                    target_res: Callable[[], Tuple[int, int]],
                    brick: LegoBrick):
        ret = brick.clone()

        source_width, source_height = source_res()
        target_width, target_height = target_res()

        ret.centroid_x = int((ret.centroid_x / source_width) * target_width)
        ret.centroid_y = int((ret.centroid_y / source_height) * target_height)

        return ret

    def get_board_res(self):
        return self.config.get("board", "width"), self.config.get("board", "height")

    def get_beamer_res(self):
        return self.last_frame.shape[0], self.last_frame.shape[1]

    def beamer_mouse_callback(self, event, x, y, flags, param):
        mouse_pos = self.beamer_to_board(LegoBrick(x, y, LegoShape.RECTANGLE_BRICK, LegoColor.BLUE_BRICK))
        LegoOutputStream.MOUSE_BRICKS_REFRESHED = True

        if event == cv2.EVENT_LBUTTONDOWN or event == cv2.EVENT_RBUTTONDOWN:
            virtual_brick = self.tracker.check_min_distance(mouse_pos, self.tracker.virtual_bricks)

            if virtual_brick:
                self.tracker.virtual_bricks.remove(virtual_brick)
            else:
                self.tracker.virtual_bricks.append(mouse_pos)
                logger.info("added mouse brick with state {}".format(mouse_pos.status.name))
