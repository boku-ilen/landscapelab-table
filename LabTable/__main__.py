import logging.config
import numpy as np

from .ProgramStage import ProgramStage, CurrentProgramStage
from .BrickDetection.BoardDetector import BoardDetector
from .BrickDetection.ShapeDetector import ShapeDetector
from .TableInputStream import LegoInputStream
from .TableOutputStream import LegoOutputStream, LegoOutputChannel
from .TableUI.MainMap import MainMap
from .TableUI.CallbackManager import CallbackManager
from .TableUI.UIElements.UISetup import setup_ui
from .TableUI.UIElements.UIElement import UIElement
from .ServerCommunication import ServerCommunication
from .BrickDetection.Tracker import Tracker
from .ConfigManager import ConfigManager
from .ParameterManager import ParameterManager
from .TableUI.QGISListenerThread import QGISListenerThread
from .SchedulerThread import SchedulerThread


# configure logging
logger = logging.getLogger(__name__)

try:
    logging.config.fileConfig('logging.conf')
    logger.info("Logging initialized")
except:
    logging.basicConfig(level=logging.INFO)
    logging.info("Could not initialize: logging.conf not found or misconfigured")

# Number of RGB channels in
# region of interest image
CHANNELS_NUMBER = 3


# this class manages the base workflow and handles the main loop
class LabTable:

    def __init__(self):

        # Initialize config manager
        self.config = ConfigManager()
        LegoOutputStream.set_beamer_config_info(self.config)

        # create ui root element and callback manager
        ui_root = UIElement()
        self.callback_manager = CallbackManager(self.config)

        self.program_stage = CurrentProgramStage(self.callback_manager.stage_change_actions)
        self.callback_manager.set_program_actions(self.program_stage)

        # Initialize parameter manager and parse arguments
        self.parser = ParameterManager(self.config)
        self.used_stream = self.parser.used_stream

        # Initialize board detection
        self.board_detector = BoardDetector(self.config, self.config.get("qr_code", "threshold"))
        self.board = self.board_detector.board

        # Initialize server communication class
        self.server = ServerCommunication(self.config, self.program_stage)
        self.scenario = self.server.get_scenario_info(self.config.get("general", "scenario"))

        # Initialize the centroid tracker
        self.tracker = Tracker(self.config, self.board, self.server, ui_root)
        self.callback_manager.set_tracker_callbacks(self.tracker)

        # initialize map, map callbacks and ui
        self.main_map = MainMap(self.config, 'main_map', self.scenario, self.server)
        self.callback_manager.set_map_callbacks(self.main_map)
        mini_map, planning_ui, progress_bar_update_function = \
            setup_ui(ui_root, self.main_map,  self.config, self.server, self.callback_manager)
        map_dict = {self.main_map.name: self.main_map, mini_map.name: mini_map}

        # Initialize and start the QGIS listener Thread
        # also request the first rendered map section
        self.qgis_listener_thread = QGISListenerThread(self.config, map_dict)
        self.qgis_listener_thread.start()
        self.main_map.request_render()
        mini_map.request_render()

        # link the progress_bar_update_function to the brick_update_callback so that it will be called whenever an asset
        # is added or removed from the server
        self.server.brick_update_callback = progress_bar_update_function

        # Initialize and start the server listener thread
        self.server_listener_thread = SchedulerThread(
            self.config,
            self.server,
            self.tracker,
            self.get_program_stage,
            progress_bar_update_function
        )
        self.server_listener_thread.start()

        # initialize the input and output stream
        self.output_stream = LegoOutputStream(
            self.main_map,
            ui_root,
            self.callback_manager,
            self.tracker,
            self.config,
            self.board,
            self.program_stage,
            self.server_listener_thread
        )
        self.callback_manager.set_output_actions(self.output_stream)
        self.input_stream = LegoInputStream(self.config, self.board, usestream=self.used_stream)

        # initialize the brick detector
        self.shape_detector = ShapeDetector(self.config, self.output_stream)

        # Flag which says whether the bricks
        # stored at the server are already marked as virtual
        self.added_stored_lego_bricks_flag = False

    # Run bricks detection and tracking code
    def run(self):

        # initialize the input stream
        self.input_stream = LegoInputStream(self.config, self.board, usestream=self.used_stream)

        # Initialize ROI as a black RGB-image
        region_of_interest = np.zeros((self.config.get("resolution", "height"),
                                       self.config.get("resolution", "width"), CHANNELS_NUMBER), np.uint8)

        logger.info("initialized input stream")

        try:

            # main loop which handles each frame
            while not self.output_stream.update(self.program_stage):

                # get the next frame
                depth_image_3d, color_image = self.input_stream.get_frame()

                # Add some additional information to the debug window
                color_image_debug = color_image.copy()
                self.output_stream.add_debug_information(color_image_debug)

                # always write the current frame to the board detection channel
                self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_BOARD_DETECTION, color_image_debug)

                # call different functions depending on program state
                if self.program_stage.current_stage == ProgramStage.WHITE_BALANCE:
                    self.white_balance(color_image)

                elif self.program_stage.current_stage == ProgramStage.FIND_CORNERS:
                    self.detect_corners(color_image)

                # in this stage bricks have "yes"/"no" meaning
                elif self.program_stage.current_stage == ProgramStage.EVALUATION:
                    self.do_lego_detection(region_of_interest, color_image)

                # in this stage bricks have assets meaning
                elif self.program_stage.current_stage == ProgramStage.PLANNING:
                    self.do_lego_detection(region_of_interest, color_image)

        finally:
            # handle the output stream correctly
            self.output_stream.close()

            # make sure the stream ends correctly
            self.input_stream.close()

            self.main_map.end()

    def white_balance(self, color_image):

        # when finished start next stage with command below
        if self.board_detector.compute_background(color_image):
            # switch to next stage if finished
            self.program_stage.next()

    # Detect the board using qr-codes polygon data saved in the array
    # -> self.board_detector.all_codes_polygons_points
    def detect_corners(self, color_image):

        logger.debug("No QR-code detector result")

        # Compute distance to the board
        self.input_stream.get_distance_to_board()

        # Find position of board corners
        all_board_corners_found = self.board_detector.detect_board(color_image)

        # if all boarders were found change channel and start next stage
        if all_board_corners_found:

            # Use distance to set possible brick size
            logger.debug("Calculate possible brick size")
            self.shape_detector.calculate_possible_lego_dimensions(self.board.distance)

            logger.debug("Used threshold for qr-codes -> {}".format(self.board.threshold_qrcode))
            self.output_stream.set_active_channel(LegoOutputChannel.CHANNEL_ROI)
            self.program_stage.next()

        # use different thresholds for board detection
        self.board_detector.adjust_threshold_qrcode()

    def do_lego_detection(self, region_of_interest, color_image):
        # If the board is detected take only the region
        # of interest and start brick detection

        # Take only the region of interest from the color image
        region_of_interest = self.board_detector.rectify_image(region_of_interest, color_image)
        region_of_interest_debug = region_of_interest.copy()

        # Initialize legos brick properties list
        potential_lego_bricks_list = []

        # detect contours in area of interest
        contours = self.shape_detector.detect_contours(region_of_interest)

        # Loop over the contours
        for contour in contours:

            # Check if the contour is a brick candidate (shape and color can be detected)
            brick_candidate = self.shape_detector.detect_brick(contour, region_of_interest)

            if brick_candidate:
                # Update the properties list of all potential bricks which are found in the frame
                potential_lego_bricks_list.append(brick_candidate)

                # mark potential brick contours
                LegoOutputStream.mark_candidates(region_of_interest_debug, contour)

        # TODO (future releases) implement this as stage transition callback in ProgramStage
        # Get already stored brick instances from server
        if self.program_stage.current_stage == ProgramStage.PLANNING \
                and not self.added_stored_lego_bricks_flag:

            self.tracker.sync_with_server_side_bricks()

            self.added_stored_lego_bricks_flag = True

        # Compute tracked bricks dictionary using the centroid tracker and set of properties
        # Mark stored bricks virtual
        tracked_lego_bricks = self.tracker.update(potential_lego_bricks_list, self.program_stage.current_stage)

        # Loop over the tracked objects and label them in the stream
        for tracked_lego_brick in tracked_lego_bricks:
            LegoOutputStream.labeling(region_of_interest_debug, tracked_lego_brick)

        # write current frame to the stream output
        self.output_stream.write_to_file(region_of_interest_debug)

        # Render shape detection images
        self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_ROI, region_of_interest_debug)

    def get_program_stage(self) -> ProgramStage:
        return self.program_stage.current_stage


# execute the main class  ' TODO: meaningful rename
if __name__ == '__main__':
    main = LabTable()
    main.run()
