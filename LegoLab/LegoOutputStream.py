from enum import Enum
import cv2
import screeninfo
from functools import partial
import numpy as np
import logging

from .ProgramStage import ProgramStage, CurrentProgramStage
from .LegoDetection.Tracker import Tracker
from .ConfigManager import ConfigManager
from .LegoUI.MainMap import MainMap
from .LegoUI.MapActions import MapActions
from .LegoUI.UIElements.UIElement import UIElement
from .LegoBricks import LegoBrick, LegoColor, LegoShape, LegoStatus
from .LegoUI.ImageHandler import ImageHandler
from .ExtentTracker import ExtentTracker
from .LegoExtent import LegoExtent
from .Board import Board
from .ServerListenerThread import ServerListenerThread

# enable logger
logger = logging.getLogger('MainLogger')

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


class LegoOutputChannel(Enum):

    CHANNEL_BOARD_DETECTION = 1
    CHANNEL_ROI = 2

    def next(self):
        value = self.value + 1
        if value > 2:
            value = 2
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
                 map_handler: MainMap,
                 ui_root: UIElement,
                 detection_ui: UIElement,
                 tracker: Tracker,
                 config: ConfigManager,
                 board: Board,
                 program_stage: CurrentProgramStage,
                 server_thread: ServerListenerThread,
                 video_output_name=None):

        self.config = config
        self.detection_ui = detection_ui
        self.extent_tracker = ExtentTracker.get_instance()
        self.board = board
        self.program_stage = program_stage
        self.server_thread = server_thread

        self.active_channel = LegoOutputChannel.CHANNEL_BOARD_DETECTION
        self.active_window = LegoOutputStream.WINDOW_NAME_DEBUG  # TODO: implement window handling

        # create debug window
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_DEBUG, cv2.WINDOW_AUTOSIZE)

        # create beamer window
        beamer_id = self.config.get("beamer-resolution", "screen-id")
        if beamer_id >= 0:
            pos_x = config.get("beamer-resolution", "pos-x")
            pos_y = config.get("beamer-resolution", "pos-y")

            logger.info("beamer coords: {} {}".format(pos_x, pos_y))

            cv2.namedWindow(LegoOutputStream.WINDOW_NAME_BEAMER, cv2.WND_PROP_FULLSCREEN)
            cv2.moveWindow(LegoOutputStream.WINDOW_NAME_BEAMER, pos_x, pos_y)
            cv2.setWindowProperty(LegoOutputStream.WINDOW_NAME_BEAMER, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
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

        # set ui_root and map handler, create empty variable for tracker
        self.ui_root = ui_root
        self.map_handler = map_handler
        self.tracker: Tracker = tracker

        # setup button map
        # reads corresponding keyboard input for action with config.get(...) and converts it to int with ord(...)
        self.BUTTON_MAP = {
            ord(config.get('button_map', 'DEBUG_CHANNEL_UP')): self.channel_up,
            ord(config.get('button_map', 'DEBUG_CHANNEL_DOWN')): self.channel_down,
            # FIXME: error shortly after the program start when NEXT_PROGRAM_STAGE used:
            # BoardDetector.py", line 400, in subtract_background
            # diff = cv2.absdiff(color_image, self.background.astype("uint8"))
            # AttributeError: 'NoneType' object has no attribute 'astype'
            #ord(config.get('button_map', 'NEXT_PROGRAM_STAGE')): self.program_stage.next(),
            ord(config.get('button_map', 'MAP_PAN_UP')): partial(map_handler.invoke, MapActions.PAN_UP),
            ord(config.get('button_map', 'MAP_PAN_DOWN')): partial(map_handler.invoke, MapActions.PAN_DOWN),
            ord(config.get('button_map', 'MAP_PAN_LEFT')): partial(map_handler.invoke, MapActions.PAN_LEFT),
            ord(config.get('button_map', 'MAP_PAN_RIGHT')): partial(map_handler.invoke, MapActions.PAN_RIGHT),
            ord(config.get('button_map', 'MAP_ZOOM_IN')): partial(map_handler.invoke, MapActions.ZOOM_IN),
            ord(config.get('button_map', 'MAP_ZOOM_OUT')): partial(map_handler.invoke, MapActions.ZOOM_OUT)
        }

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
        self.brick_internal = image_handler.load_image("internal_brick")
        self.brick_windmill = image_handler.load_image("windmill_brick")
        self.brick_pv = image_handler.load_image("pv_brick")
        self.icon_windmill = image_handler.load_image("windmill_icon")
        self.icon_pv = image_handler.load_image("pv_icon")
        self.icon_yes = image_handler.load_image("yes_icon")
        self.icon_no = image_handler.load_image("no_icon")
        self.player_teleport = image_handler.load_image("player_teleport")
        self.player_position = image_handler.load_image("player_position")

    # fetches the correct monitor for the beamer output and writes it's data to the ConfigManager
    @staticmethod
    def set_beamer_config_info(config):
        beamer_id = config.get("beamer-resolution", "screen-id")
        if beamer_id >= 0:
            monitors = screeninfo.get_monitors()

            # if beamer-id out of bounds use last screen
            beamer_id = min(beamer_id, len(monitors) - 1)

            beamer = monitors[beamer_id]
            config.set("beamer-resolution", "width", beamer.width)
            config.set("beamer-resolution", "height", beamer.height)
            config.set("beamer-resolution", "pos-x", beamer.x - 1)
            config.set("beamer-resolution", "pos-y", beamer.y - 1)

            ExtentTracker.get_instance().beamer = LegoExtent(0, 0, beamer.width, beamer.height)

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

    # we label the identified lego bricks in the stream
    @staticmethod
    def labeling(frame, tracked_lego_brick: LegoBrick):
        # Draw lego bricks IDs
        text = "ID {}".format(tracked_lego_brick.assetpos_id)
        tracked_lego_brick_position = tracked_lego_brick.centroid_x, tracked_lego_brick.centroid_y
        cv2.putText(frame, text, (tracked_lego_brick.centroid_x - BRICK_LABEL_OFFSET,
                                  tracked_lego_brick.centroid_y - BRICK_LABEL_OFFSET),
                    cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, DARK_GRAY, FONT_THICKNESS)

        # Draw lego bricks contour names
        # FIXME: put other caption like id of the lego brick
        cv2.putText(frame, tracked_lego_brick.status.name, tracked_lego_brick_position,
                    cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, DARK_GRAY, FONT_THICKNESS)

        # Draw lego bricks centroid points
        cv2.circle(frame, tracked_lego_brick_position, RADIUS, GREEN, cv2.FILLED)

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

        # call button callback
        if key in self.BUTTON_MAP:
            self.BUTTON_MAP[key]()

        # TODO: use button_map for all keys
        # n -> change from EVALUATION to LEGO_DETECTION program stage
        if program_stage.current_stage == ProgramStage.EVALUATION and key == 110:
            self.detection_ui.set_visible(True)
            program_stage.next()

        # Break with Esc  # FIXME: CG: keyboard might not be available - use signals?
        if key == 27:
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
                or program_stage.current_stage == ProgramStage.LEGO_DETECTION:
            self.redraw_lego_detection()

    # displays a white screen
    # so that the board detector can more easily detect the qr-codes later
    # called every frame when in ProgramStage WHITE_BALANCE
    def draw_white_frame(self):
        frame = np.ones([
            self.config.get("beamer-resolution", "height"),
            self.config.get("beamer-resolution", "width"),
            4
        ]) * 255
        cv2.imshow(LegoOutputStream.WINDOW_NAME_BEAMER, frame)
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
        cv2.imshow(LegoOutputStream.WINDOW_NAME_BEAMER, frame)

    # checks if the frame has updated and redraws it if this is the case
    # called every frame when in ProgramStage LEGO_DETECTION
    def redraw_lego_detection(self):
        # check flags if any part of the frame has changed
        if self.config.get("map_settings", 'map_refreshed') \
                or self.config.get("ui-settings", "ui-refreshed") \
                or Tracker.BRICKS_REFRESHED \
                or LegoOutputStream.MOUSE_BRICKS_REFRESHED:

            # get map image from map handler
            frame = self.map_handler.get_map_image().copy()

            # render virtual external bricks on top of map
            self.render_external_virtual_bricks(frame)

            # render ui over map and external virtual bricks
            self.ui_root.draw(frame)

            # render remaining bricks in front of ui
            self.render_bricks(frame)

            # display and save frame
            cv2.imshow(LegoOutputStream.WINDOW_NAME_BEAMER, frame)
            self.last_frame = frame

            # reset flags
            self.config.set("map_settings", "map_refreshed", False)
            self.config.set("ui-settings", "ui-refreshed", False)
            Tracker.BRICKS_REFRESHED = False
            LegoOutputStream.MOUSE_BRICKS_REFRESHED = False

    # renders only external virtual bricks
    # since they should be displayed behind the ui unlike any other brick types
    def render_external_virtual_bricks(self, render_target):
        # render bricks on top of transparent overlay_target
        overlay_target = render_target.copy()

        # filter external bricks out of the virtual brick list and iterate over them
        for brick in filter(lambda b: b.status == LegoStatus.EXTERNAL_BRICK, self.tracker.virtual_bricks):
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
        for brick in list(filter(lambda b: b.status != LegoStatus.EXTERNAL_BRICK, self.tracker.virtual_bricks)):
            self.render_brick(brick, overlay_target, True)

        # add overlay_target to render_target with alpha_value
        cv2.addWeighted(overlay_target, VIRTUAL_BRICK_ALPHA, render_target, 1 - VIRTUAL_BRICK_ALPHA, 0, render_target)

    # renders a given brick onto a given render target
    # fetches the correct icon with get_brick_icon
    def render_brick(self, brick, render_target, virtual=False):
        b = LegoExtent.remap(brick, self.extent_tracker.board, self.extent_tracker.beamer)
        pos = (int(b.centroid_x), int(b.centroid_y))
        icon = self.get_brick_icon(brick, virtual)

        ImageHandler.img_on_background(render_target, icon, pos)

    # returns the correct brick icon for any given brick
    def get_brick_icon(self, brick, virtual):

        if brick.status == LegoStatus.OUTDATED_BRICK:
            return self.brick_outdated

        elif brick.status == LegoStatus.INTERNAL_BRICK:
            return self.brick_internal

        else:
            # set different icons for if brick is virtual
            if virtual and (brick.asset_id == 1 or brick.asset_id == 2):
                return self.icon_pv
            elif virtual and brick.asset_id == 3:
                return self.icon_windmill

            # set icons if brick is not virtual
            # or icons are the same independently of virtual-property
            if brick.asset_id == 1 or brick.asset_id == 2:
                return self.brick_pv
            elif brick.asset_id == 3:
                return self.brick_windmill
            elif brick.asset_id == 4:
                return self.player_teleport
            elif brick.asset_id == 13:
                return self.player_position
            # allow only square bricks for yes / no
            elif brick.shape == LegoShape.SQUARE_BRICK:
                if brick.asset_id == 11:
                    return self.icon_yes
                elif brick.asset_id == 12:
                    return self.icon_no
            else:
                # rectangle bricks are marked as outdated
                # but create request is pushed anyway
                return self.brick_outdated

    # closing the outputstream if it is defined
    def close(self):
        self.server_thread.ticker.set()
        logger.info("exit")
        logging.shutdown()
        cv2.destroyAllWindows()
        if self.video_handler:
            self.video_handler.release()

    # creates or deletes virtual bricks on mouse click
    # parameters flags and param are necessary so that function can be registered as openCV mouse callback function
    def beamer_mouse_callback(self, event, x, y, flags, param):

        if self.program_stage.current_stage == ProgramStage.EVALUATION \
                or self.program_stage.current_stage == ProgramStage.LEGO_DETECTION:

            if event == cv2.EVENT_LBUTTONDOWN or event == cv2.EVENT_RBUTTONDOWN:

                color = LegoColor.BLUE_BRICK
                if event == cv2.EVENT_RBUTTONDOWN:
                    color = LegoColor.RED_BRICK

                # create brick on mouse position
                mouse_brick = LegoExtent.remap(
                    LegoBrick(x, y, LegoShape.SQUARE_BRICK, color),
                    self.extent_tracker.beamer, self.extent_tracker.board
                )

                # check for nearby virtual bricks
                virtual_brick = self.tracker.check_min_distance(mouse_brick, self.tracker.virtual_bricks)

                if virtual_brick and virtual_brick.asset_id != PLAYER_POSITION_ASSET_ID:
                    # if mouse brick is on top of other virtual brick, remove that brick
                    self.tracker.remove_external_virtual_brick(virtual_brick)
                else:
                    # otherwise add the mouse brick
                    self.tracker.virtual_bricks.append(mouse_brick)

                # set mouse brick refreshed flag
                LegoOutputStream.MOUSE_BRICKS_REFRESHED = True
