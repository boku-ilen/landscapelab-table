from enum import Enum
import cv2
import screeninfo
import numpy as np
import logging
from typing import List

from LabTable.Model.ProgramStage import ProgramStage, CurrentProgramStage
from LabTable.BrickDetection.Tracker import Tracker
from LabTable.Configurator import Configurator
from LabTable.TableUI.MainMap import MainMap
from LabTable.TableUI.UIElements.UIElement import UIElement
from LabTable.Model.Brick import Brick, BrickColor, BrickShape, BrickStatus, Token
from LabTable.TableUI.ImageHandler import ImageHandler
from LabTable.TableUI.CallbackManager import CallbackManager
from LabTable.ExtentTracker import ExtentTracker
from LabTable.Model.Extent import Extent
from LabTable.Model.Board import Board

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
DEBUG_FONT_SIZE = 0.8
DEBUG_FONT_THICKNESS = 2
POSITION_X = 20
POSITION_Y = 20
LINE_HEIGHT = 20


class TableOutputChannel(Enum):

    CHANNEL_BOARD_DETECTION = 1
    CHANNEL_QR_DETECTION = 3
    CHANNEL_ROI = 2

    def next(self):
        value = self.value + 1
        if value > 3:
            value = 3
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
                 ui_root: UIElement,
                 callback_manager: CallbackManager,
                 tracker: Tracker,
                 config: Configurator,
                 board: Board,
                 program_stage: CurrentProgramStage,
                 video_output_name=None):

        self.config = config
        self.callback_manager = callback_manager
        self.extent_tracker = ExtentTracker.get_instance()
        self.board = board
        self.program_stage = program_stage

        self.active_channel = TableOutputChannel.CHANNEL_BOARD_DETECTION
        self.active_window = TableOutputStream.WINDOW_NAME_DEBUG

        # create a store of the last images of each channel
        self.channel_images = {}
        for channel in TableOutputChannel:
            self.channel_images[channel.name] = np.empty((1, 1))

        # create debug window
        cv2.namedWindow(TableOutputStream.WINDOW_NAME_DEBUG, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(TableOutputStream.WINDOW_NAME_DEBUG, config.get("screen_resolution", "width"),
                         config.get("screen_resolution", "height"))

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
            self.video_handler = cv2.VideoWriter(video_output_name, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                                 10, (config.get('video_resolution', 'width'),
                                                      config.get('video_resolution', 'height')))
        else:
            self.video_handler = None

        self.last_frame = None

        # set ui_root and map handler, create empty variable for tracker
        self.ui_root = ui_root
        self.tracker: Tracker = tracker

        # create image handler to load images
        self.image_handler = ImageHandler(config)

        # load qr code images
        qr_size = self.config.get("qr_code", "size")
        # TODO calc optimal size on draw instead of scaling down to fixed size
        self.qr_bottom_left = self.image_handler.load_image("qr_bottom_left", (qr_size, qr_size))
        self.qr_bottom_right = self.image_handler.load_image("qr_bottom_right", (qr_size, qr_size))
        self.qr_top_left = self.image_handler.load_image("qr_top_left", (qr_size, qr_size))
        self.qr_top_right = self.image_handler.load_image("qr_top_right", (qr_size, qr_size))

        # load brick overlay images
        self.brick_outdated = self.image_handler.load_image("outdated_brick")
        self.brick_unknown = self.image_handler.load_image("unknown_brick")
        self.brick_internal = self.image_handler.load_image("internal_brick")

        # load and initialize icon lists
        self.brick_icons = {}
        self.virtual_icons = {}
        self.brick_icons["windmill_icon"] = self.image_handler.load_image("windmill_brick")
        self.brick_icons["pv_icon"] = self.image_handler.load_image("pv_brick")
        self.virtual_icons["windmill_icon"] = self.image_handler.load_image("windmill_icon")
        self.virtual_icons["pv_icon"] = self.image_handler.load_image("pv_icon")

    # fetches the correct monitor for the beamer output and writes it's data to the ConfigManager
    @staticmethod
    def set_screen_config_info(config):

        monitors = screeninfo.get_monitors()

        config.set("screen_resolution", "width", monitors[0].width)
        config.set("screen_resolution", "height", monitors[0].height)
        config.set("screen_resolution", "pos_x", monitors[0].x - 1)
        config.set("screen_resolution", "pos_y", monitors[0].y - 1)

        beamer_id = config.get("beamer_resolution", "screen_id")
        if beamer_id >= 0:
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

        # display the channel name in the frame
        cv2.putText(frame, channel.name, (POSITION_X, POSITION_Y), cv2.FONT_HERSHEY_DUPLEX, DEBUG_FONT_SIZE, GREEN,
                    DEBUG_FONT_THICKNESS)

        # store the last frame for later display
        self.channel_images[channel.name] = frame

    # change the active channel, which is displayed in the window
    def set_active_channel(self, channel):
        self.active_channel = channel

    # changes to the next channel
    def channel_up(self):
        logger.debug("changed active channel one up")
        self.set_active_channel(self.active_channel.next())

    # changes to the previous channel
    def channel_down(self):
        logger.debug("changed active channel one down")
        self.set_active_channel(self.active_channel.prev())

    # mark the candidate in given frame
    @staticmethod
    def mark_candidates(frame, candidate_contour):
        cv2.drawContours(frame, [candidate_contour], IDX_DRAW_ALL, DARK_GRAY, CONTOUR_THICKNESS)

    # we label the identified bricks in the stream
    @staticmethod
    def labeling(frame, tracked_brick: Brick):
        # Draw brick IDs
        text = "Hue {}".format(tracked_brick.average_detected_color)
        tracked_brick_position = tracked_brick.centroid_x, tracked_brick.centroid_y
        cv2.putText(frame, text, (tracked_brick.centroid_x - BRICK_LABEL_OFFSET,
                                  tracked_brick.centroid_y - BRICK_LABEL_OFFSET),
                    cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, DARK_GRAY, FONT_THICKNESS)

        # Draw brick contour names
        caption = "{} ({}, {})".format(tracked_brick.status.name, tracked_brick.centroid_x, tracked_brick.centroid_y)
        cv2.putText(frame, caption, tracked_brick_position, cv2.FONT_HERSHEY_SIMPLEX, FONT_SIZE, DARK_GRAY,
                    FONT_THICKNESS)

        # Draw brick centroid points
        cv2.circle(frame, tracked_brick_position, RADIUS, GREEN, cv2.FILLED)

    # called every frame, updates the beamer image and recognizes and handles button presses
    def update(self, program_stage: CurrentProgramStage) -> bool:

        # update beamer image if necessary
        self.redraw_beamer_image(program_stage)

        # redraw debug window
        cv2.imshow(self.active_window, self.channel_images[self.active_channel.name])

        # check if key pressed
        key = cv2.waitKeyEx(1)

        self.callback_manager.call_key_action(key)

        # Break with Esc  # FIXME: CG: keyboard might not be available - use signals?
        if key == 27:
            logger.info("quit the program with the key")
            return True
        return False

    # redraws the beamer image if necessary with the correct frame depending on the ProgramStage
    # TODO: maybe make the image configurable via the GameEngine?
    def redraw_beamer_image(self, program_stage: CurrentProgramStage):

        if program_stage.current_stage == ProgramStage.WHITE_BALANCE:
            self.draw_white_frame()

        elif program_stage.current_stage == ProgramStage.FIND_CORNERS:
            self.draw_corner_qr_codes()

        else:
            self.redraw_brick_detection()

    # displays a white screen so that the board detector can more easily detect the qr-codes later
    # called every frame when in ProgramStage WHITE_BALANCE
    def draw_white_frame(self):
        frame = np.ones([
            self.config.get("beamer_resolution", "height"),
            self.config.get("beamer_resolution", "width"),
            4
        ]) * 255
        cv2.imshow(TableOutputStream.WINDOW_NAME_BEAMER, frame)
        self.last_frame = frame

    # displays qr-codes in each corner for the detection of the game board dimensions
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
    # called every frame when running the actual game
    def redraw_brick_detection(self):

        # check flags if any part of the frame has changed
        if self.config.get("map_settings", 'map_refreshed') \
                or self.config.get("ui_settings", "ui_refreshed") \
                or Tracker.BRICKS_REFRESHED \
                or TableOutputStream.MOUSE_BRICKS_REFRESHED:

            # get map image from map handler
            resolution_x = int(self.config.get("beamer_resolution", "width"))
            resolution_y = int(self.config.get("beamer_resolution", "height"))

            frame = ImageHandler.ensure_alpha_channel(np.ones((resolution_y, resolution_x, 3), np.uint8) * 255)

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
        return
        
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
    def get_brick_icon(self, brick: Brick, virtual):

        # return x icon if brick is outdated
        if brick.status == BrickStatus.OUTDATED_BRICK:
            return self.brick_outdated

        # search for correct internal icon and return it if brick is internal
        elif brick.status == BrickStatus.INTERNAL_BRICK:
            # FIXME: Not 100% sure but i am not aware of another state than an internal-brick
            # visualizing the green square
            return self.brick_internal

        # search for correct internal icon and return it if brick is external
        elif brick.status == BrickStatus.EXTERNAL_BRICK:
            # FIXME:
            
            lookup_dict = self.virtual_icons if virtual else self.brick_icons 

            if hasattr(brick, "token"):# and brick.token.svg != "" and brick.token.svg != None:
                try:
                    # This should actually not be the case but for safety reasons
                    if not brick.token.svg in lookup_dict:
                        return self.image_handler.load_image(brick.token.svg)
                    return lookup_dict[brick.token.svg]

                except Exception as e:
                    logger.error(
                        "Could not load image with config identifier: {}".format(brick.token.svg))
                    logger.error("closing because encountered a problem: {}".format(e))
                    logger.exception(e)
                    return self.brick_unknown

        # return "unknown brick" icon if no icon matches
        return self.brick_unknown

    # closing the outputstream if it is defined
    def close(self):
        logger.info("closing table output stream")
        logging.shutdown()
        cv2.destroyAllWindows()
        if self.video_handler:
            self.video_handler.release()

    # creates or deletes virtual bricks on mouse click
    # parameters flags and param are necessary so that function can be registered as openCV mouse callback function
    def beamer_mouse_callback(self, event, x, y, flags, param):

        if self.program_stage.current_stage == ProgramStage.INTERNAL_MODE \
                or self.program_stage.current_stage == ProgramStage.EXTERNAL_MODE:

            if event == cv2.EVENT_LBUTTONDOWN or event == cv2.EVENT_RBUTTONDOWN:

                color = BrickColor.BLUE_BRICK
                if event == cv2.EVENT_RBUTTONDOWN:
                    color = BrickColor.RED_BRICK

                # create brick on mouse position
                mouse_brick = Extent.remap_brick(Brick(x, y, Token(BrickShape.SQUARE_BRICK, color)),
                                                 
                    self.extent_tracker.beamer, self.extent_tracker.board
                )

                # check for nearby virtual bricks
                virtual_brick = self.tracker.check_min_distance(mouse_brick, self.tracker.virtual_bricks)

                if virtual_brick:
                    # if mouse brick is on top of other virtual brick, remove that brick
                    self.tracker.remove_external_virtual_brick(virtual_brick)
                else:
                    # otherwise add the mouse brick
                    self.tracker.virtual_bricks.append(mouse_brick)

                # set mouse brick refreshed flag
                TableOutputStream.MOUSE_BRICKS_REFRESHED = True
