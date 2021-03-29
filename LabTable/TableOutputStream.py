from enum import Enum
import cv2
import screeninfo
import numpy as np
import logging
from typing import List

from LabTable.Model.ProgramStage import ProgramStage, CurrentProgramStage
from .BrickDetection.Tracker import Tracker
from .Configurator import Configurator
from .TableUI.MainMap import MainMap
from .TableUI.UIElements.UIElement import UIElement
from LabTable.Model.Brick import Brick, BrickColor, BrickShape, BrickStatus
from .TableUI.ImageHandler import ImageHandler
from .TableUI.BrickIcon import ExternalBrickIcon, InternalBrickIcon
from .TableUI.CallbackManager import CallbackManager
from .ExtentTracker import ExtentTracker
from LabTable.Model.Extent import Extent
from LabTable.Model.Board import Board
from .SchedulerThread import SchedulerThread

# enable logger
logger = logging.getLogger(__name__)

# drawing constants
BRICK_DISPLAY_SIZE = 10
VIRTUAL_BRICK_ALPHA = 0.3
BRICK_LABEL_OFFSET = 10
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
RED = (0, 0, 255)
DARK_GRAY = (40, 40, 40)
FONT_SIZE = 0.4
FONT_THICKNESS = 1
CONTOUR_THICKNESS = 1
IDX_DRAW_ALL = -1
RADIUS = 3

# drawing debug information constants
DEBUG_INFORMATION_FONT_SIZE = 0.8
POSITION_X = 20
POSITION_Y = 20
LINE_HEIGHT = 20

PLAYER_POSITION_ASSET_ID = 13


class TableOutputChannel(Enum):

    CHANNEL_BOARD_DETECTION = 1
    CHANNEL_ROI = 2

    def next(self):
        value = self.value + 1
        if value > 2:
            value = 2
        return TableOutputChannel(value)

    def prev(self):
        value = self.value - 1
        if value < 1:
            value = 1
        return TableOutputChannel(value)


# this class handles the output video streams
class TableOutputStream:

    WINDOW_NAME_DEBUG = 'DEBUG WINDOW'
    WINDOW_NAME_BEAMER = 'BEAMER WINDOW'

    MOUSE_BRICKS_REFRESHED = False

    def __init__(self,
                 map_handler: MainMap,
                 ui_root: UIElement,
                 callback_manager: CallbackManager,
                 tracker: Tracker,
                 config: Configurator,
                 board: Board,
                 program_stage: CurrentProgramStage,
                 server_thread: SchedulerThread,
                 video_output_name=None):

        self.config = config
        self.callback_manager = callback_manager
        self.extent_tracker = ExtentTracker.get_instance()
        self.board = board
        self.program_stage = program_stage
        self.server_thread = server_thread

        self.active_channel = TableOutputChannel.CHANNEL_BOARD_DETECTION
        self.active_window = TableOutputStream.WINDOW_NAME_DEBUG  # TODO: implement window handling

        # create debug window
        cv2.namedWindow(TableOutputStream.WINDOW_NAME_DEBUG, cv2.WINDOW_AUTOSIZE)

        # create beamer window
        beamer_id = self.config.get("beamer_resolution", "screen_id")
        if beamer_id >= 0:
            pos_x = config.get("beamer_resolution", "pos_x")
            pos_y = config.get("beamer_resolution", "pos_y")

            logger.info("beamer coords: {} {}".format(pos_x, pos_y))

            cv2.namedWindow(TableOutputStream.WINDOW_NAME_BEAMER, cv2.WND_PROP_FULLSCREEN)
            cv2.moveWindow(TableOutputStream.WINDOW_NAME_BEAMER, pos_x, pos_y)
            cv2.setWindowProperty(TableOutputStream.WINDOW_NAME_BEAMER, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.namedWindow(TableOutputStream.WINDOW_NAME_BEAMER, cv2.WINDOW_AUTOSIZE)
        cv2.setMouseCallback(TableOutputStream.WINDOW_NAME_BEAMER, self.beamer_mouse_callback)

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

        # set ui_root and map handler, create empty variable for tracker
        self.ui_root = ui_root
        self.map_handler = map_handler
        self.tracker: Tracker = tracker

        # create image handler to load images
        image_handler = ImageHandler(config)

        # load qr code images
        qr_size = self.config.get("resources", "qr_size")
        # TODO calc optimal size on draw instead of scaling down to fixed size
        self.qr_bottom_left = image_handler.load_image("qr_bottom_left", (qr_size, qr_size))
        self.qr_bottom_right = image_handler.load_image("qr_bottom_right", (qr_size, qr_size))
        self.qr_top_left = image_handler.load_image("qr_top_left", (qr_size, qr_size))
        self.qr_top_right = image_handler.load_image("qr_top_right", (qr_size, qr_size))

        # load brick overlay images
        self.brick_outdated = image_handler.load_image("outdated_brick")
        self.brick_unknown = image_handler.load_image("unknown_brick")

        # load and initialize icon lists
        internal_icons = config.get("brick_icon_mappings", "internal_bricks")
        external_icons = config.get("brick_icon_mappings", "external_bricks")
        self.internal_icon_list: List[InternalBrickIcon] = []
        self.external_icon_list: List[ExternalBrickIcon] = []

        for rule, icon_name in internal_icons.items():
            self.internal_icon_list.append(InternalBrickIcon(rule, image_handler.load_image(icon_name)))

        for rule, icon_name in external_icons.items():
            self.external_icon_list.append(ExternalBrickIcon(rule, image_handler.load_image(icon_name)))

    # fetches the correct monitor for the beamer output and writes it's data to the ConfigManager
    @staticmethod
    def set_beamer_config_info(config):
        beamer_id = config.get("beamer_resolution", "screen_id")
        if beamer_id >= 0:
            monitors = screeninfo.get_monitors()

            # if beamer-id out of bounds use last screen
            beamer_id = min(beamer_id, len(monitors) - 1)

            beamer = monitors[beamer_id]
            config.set("beamer_resolution", "width", beamer.width)
            config.set("beamer_resolution", "height", beamer.height)
            config.set("beamer_resolution", "pos_x", beamer.x - 1)
            config.set("beamer_resolution", "pos_y", beamer.y - 1)

            ExtentTracker.get_instance().beamer = Extent(0, 0, beamer.width, beamer.height)

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

    # changes to the next channel
    def channel_up(self):
        logger.info("changed active channel one up")
        self.set_active_channel(self.active_channel.next())

    # changes to the previous channel
    def channel_down(self):
        logger.info("changed active channel one down")
        self.set_active_channel(self.active_channel.prev())

    # mark the candidate in given frame
    @staticmethod
    def mark_candidates(frame, candidate_contour):
        cv2.drawContours(frame, [candidate_contour], IDX_DRAW_ALL, DARK_GRAY, CONTOUR_THICKNESS)

    # we label the identified bricks in the stream
    @staticmethod
    def labeling(frame, tracked_brick: Brick):
        # Draw brick IDs
        text = "ID {}".format(tracked_brick.object_id)
        tracked_brick_position = tracked_brick.centroid_x, tracked_brick.centroid_y
        cv2.putText(frame, text, (tracked_brick.centroid_x - BRICK_LABEL_OFFSET,
                                  tracked_brick.centroid_y - BRICK_LABEL_OFFSET),
                    cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, DARK_GRAY, FONT_THICKNESS)

        # Draw brick contour names
        # FIXME: put other caption like id of the brick
        cv2.putText(frame, tracked_brick.status.name, tracked_brick_position,
                    cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, DARK_GRAY, FONT_THICKNESS)

        # Draw brick centroid points
        cv2.circle(frame, tracked_brick_position, RADIUS, GREEN, cv2.FILLED)

    # Add some additional information to the debug window
    def add_debug_information(self, frame):

        text = "threshold: " + str(self.board.threshold_qrcode) \
                         + "\nnumber of found qr-codes: " + str(self.board.found_codes_number)

        # Add text line by line
        for line_number, line in enumerate(text.split("\n")):
            position_y = POSITION_Y + line_number * LINE_HEIGHT
            cv2.putText(frame, line, (POSITION_X, position_y),
                        cv2.FONT_HERSHEY_SIMPLEX, DEBUG_INFORMATION_FONT_SIZE, GREEN, FONT_THICKNESS)

    # called every frame, updates the beamer image
    # recognizes and handles button presses
    def update(self, program_stage: CurrentProgramStage) -> bool:
        # update beamer image if necessary
        self.redraw_beamer_image(program_stage)

        # check if key pressed
        key = cv2.waitKeyEx(1)

        self.callback_manager.call_key_action(key)

        # Break with Esc  # FIXME: CG: keyboard might not be available - use signals?
        if key == 27:
            logger.info("quit the program with the key")
            return True
        return False

    # redraws the beamer image if necessary
    # applies different logic for each program_stage
    def redraw_beamer_image(self, program_stage: CurrentProgramStage):

        if program_stage.current_stage == ProgramStage.WHITE_BALANCE:
            self.draw_white_frame()

        elif program_stage.current_stage == ProgramStage.FIND_CORNERS:
            self.draw_corner_qr_codes()

        elif program_stage.current_stage == ProgramStage.EVALUATION \
                or program_stage.current_stage == ProgramStage.PLANNING:
            self.redraw_brick_detection()

    # displays a white screen
    # so that the board detector can more easily detect the qr-codes later
    # called every frame when in ProgramStage WHITE_BALANCE
    def draw_white_frame(self):
        frame = np.ones([
            self.config.get("beamer_resolution", "height"),
            self.config.get("beamer_resolution", "width"),
            4
        ]) * 255
        cv2.imshow(TableOutputStream.WINDOW_NAME_BEAMER, frame)
        self.last_frame = frame

    # displays qr-codes in each corner
    # so that the board detector can correctly identify the beamer projection edges
    # called every frame when in ProgramStage FIND_CORNERS
    def draw_corner_qr_codes(self):
        frame = self.last_frame

        # calculate qr-code offsets
        pos_top_left = (0, 0)
        pos_top_right = (frame.shape[1] - self.qr_top_right['image'].shape[1], 0)
        pos_bottom_left = (0, frame.shape[0] - self.qr_bottom_left['image'].shape[0])
        pos_bottom_right = (
            frame.shape[1] - self.qr_bottom_right['image'].shape[1],
            frame.shape[0] - self.qr_bottom_right['image'].shape[0]
        )

        # display images with calculated offsets
        ImageHandler.img_on_background(frame, self.qr_top_left, pos_top_left)
        ImageHandler.img_on_background(frame, self.qr_top_right, pos_top_right)
        ImageHandler.img_on_background(frame, self.qr_bottom_left, pos_bottom_left)
        ImageHandler.img_on_background(frame, self.qr_bottom_right, pos_bottom_right)
        cv2.imshow(TableOutputStream.WINDOW_NAME_BEAMER, frame)

    # checks if the frame has updated and redraws it if this is the case
    # called every frame when in ProgramStage EVALUATION or PLANNING
    def redraw_brick_detection(self):
        # check flags if any part of the frame has changed
        if self.config.get("map_settings", 'map_refreshed') \
                or self.config.get("ui_settings", "ui_refreshed") \
                or Tracker.BRICKS_REFRESHED \
                or TableOutputStream.MOUSE_BRICKS_REFRESHED:

            # get map image from map handler
            frame = self.map_handler.get_map_image().copy()

            # render virtual external bricks on top of map
            self.render_external_virtual_bricks(frame)

            # render ui over map and external virtual bricks
            self.ui_root.draw(frame)

            # render remaining bricks in front of ui
            self.render_bricks(frame)

            # display and save frame
            cv2.imshow(TableOutputStream.WINDOW_NAME_BEAMER, frame)
            self.last_frame = frame

            # reset flags
            self.config.set("map_settings", "map_refreshed", False)
            self.config.set("ui_settings", "ui_refreshed", False)
            Tracker.BRICKS_REFRESHED = False
            TableOutputStream.MOUSE_BRICKS_REFRESHED = False

    # renders only external virtual bricks
    # since they should be displayed behind the ui unlike any other brick types
    def render_external_virtual_bricks(self, render_target):
        # render bricks on top of transparent overlay_target
        overlay_target = render_target.copy()

        # filter external bricks out of the virtual brick list and iterate over them
        for brick in filter(lambda b: b.status == BrickStatus.EXTERNAL_BRICK, self.tracker.virtual_bricks):
            self.render_brick(brick, overlay_target, True)

        # add overlay_target to render_target with alpha_value
        cv2.addWeighted(overlay_target, VIRTUAL_BRICK_ALPHA, render_target, 1 - VIRTUAL_BRICK_ALPHA, 0, render_target)

    # renders all bricks except external virtual ones since those get rendered earlier
    def render_bricks(self, render_target):
        # render all confirmed bricks without transparency
        for brick in self.tracker.confirmed_bricks:
            self.render_brick(brick, render_target)

        # render virtual bricks on top of transparent overlay_target
        overlay_target = render_target.copy()
        # iterate over all non-external virtual bricks and draw them to the overlay_target
        for brick in list(filter(lambda b: b.status != BrickStatus.EXTERNAL_BRICK, self.tracker.virtual_bricks)):
            self.render_brick(brick, overlay_target, True)

        # add overlay_target to render_target with alpha_value
        cv2.addWeighted(overlay_target, VIRTUAL_BRICK_ALPHA, render_target, 1 - VIRTUAL_BRICK_ALPHA, 0, render_target)

    # renders a given brick onto a given render target
    # fetches the correct icon with get_brick_icon
    def render_brick(self, brick, render_target, virtual=False):
        b = Extent.remap_brick(brick, self.extent_tracker.board, self.extent_tracker.beamer)
        pos = (int(b.centroid_x), int(b.centroid_y))
        icon = self.get_brick_icon(brick, virtual)

        ImageHandler.img_on_background(render_target, icon, pos)

    # returns the correct brick icon for any given brick
    def get_brick_icon(self, brick, virtual):

        # return x icon if brick is outdated
        if brick.status == BrickStatus.OUTDATED_BRICK:
            return self.brick_outdated

        # search for correct internal icon and return it if brick is internal
        elif brick.status == BrickStatus.INTERNAL_BRICK:
            for icon_candidate in self.internal_icon_list:
                if icon_candidate.matches(brick):
                    return icon_candidate.icon

        # search for correct internal icon and return it if brick is external
        elif brick.status == BrickStatus.EXTERNAL_BRICK:
            for icon_candidate in self.external_icon_list:
                if icon_candidate.matches(brick, virtual):
                    return icon_candidate.icon

        # return "unknown brick" icon if no icon matches
        return self.brick_unknown

    # closing the outputstream if it is defined
    def close(self):
        self.server_thread.ticker.set()
        logger.info("closing table output stream")
        logging.shutdown()
        cv2.destroyAllWindows()
        if self.video_handler:
            self.video_handler.release()

    # creates or deletes virtual bricks on mouse click
    # parameters flags and param are necessary so that function can be registered as openCV mouse callback function
    def beamer_mouse_callback(self, event, x, y, flags, param):

        if self.program_stage.current_stage == ProgramStage.EVALUATION \
                or self.program_stage.current_stage == ProgramStage.PLANNING:

            if event == cv2.EVENT_LBUTTONDOWN or event == cv2.EVENT_RBUTTONDOWN:

                color = BrickColor.BLUE_BRICK
                if event == cv2.EVENT_RBUTTONDOWN:
                    color = BrickColor.RED_BRICK

                # create brick on mouse position
                mouse_brick = Extent.remap_brick(
                    Brick(x, y, BrickShape.SQUARE_BRICK, color),
                    self.extent_tracker.beamer, self.extent_tracker.board
                )

                # check for nearby virtual bricks
                virtual_brick = self.tracker.check_min_distance(mouse_brick, self.tracker.virtual_bricks)

                if virtual_brick and virtual_brick.layer_id != PLAYER_POSITION_ASSET_ID:
                    # if mouse brick is on top of other virtual brick, remove that brick
                    self.tracker.remove_external_virtual_brick(virtual_brick)
                else:
                    # otherwise add the mouse brick
                    self.tracker.virtual_bricks.append(mouse_brick)

                # set mouse brick refreshed flag
                TableOutputStream.MOUSE_BRICKS_REFRESHED = True
