import logging.config
import numpy as np

from .ProgramStage import ProgramStage
from .LegoDetection.BoardDetector import BoardDetector
from .LegoDetection.ShapeDetector import ShapeDetector
from .LegoInputStream import LegoInputStream
from .LegoOutputStream import LegoOutputStream, LegoOutputChannel
from .LegoUI.MainMap import MainMap
from .LegoUI.UIElements.UISetup import setup_ui
from .ServerCommunication import ServerCommunication
from .LegoDetection.Tracker import Tracker
from .ConfigManager import ConfigManager
from .ParameterManager import ParameterManager
from .LegoUI.ListenerThread import ListenerThread


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
class LegoLab:

    def __init__(self):

        # Initialize config manager
        self.config = ConfigManager()
        LegoOutputStream.set_beamer_config_info(self.config)

        self.program_stage = ProgramStage.WHITE_BALANCE

        # Initialize parameter manager and parse arguments
        self.parser = ParameterManager(self.config)
        self.used_stream = self.parser.used_stream

        # Initialize board detection
        self.board_detector = BoardDetector(self.config, self.config.get("qr_code", "threshold"))
        self.board = self.board_detector.board

        # Initialize server communication class
        self.server = ServerCommunication(self.config, self.board)
        self.scenario = self.server.get_scenario_info(self.config.get("general", "scenario"))

        # initialize map handler and ui
        self.main_map = MainMap(self.config, self.scenario)
        ui_root = setup_ui(self.main_map.action_map, self.config)

        # Initialize the centroid tracker
        self.tracker = Tracker(self.config, self.board, self.server, ui_root)

        # initialize the input and output stream
        self.output_stream = LegoOutputStream(self.main_map, ui_root, self.tracker, self.config, self.board)
        self.input_stream = LegoInputStream(self.config, self.board, usestream=self.used_stream)

        # Initialize and start the QGIS listener Thread
        # also request the first rendered map section
        self.listener_thread = ListenerThread(self.config, self.main_map)
        self.listener_thread.start()
        self.main_map.request_render()

        # initialize the lego detector
        self.shape_detector = ShapeDetector(self.config, self.output_stream)

    # Run lego bricks detection and tracking code
    def run(self):

        # initialize the input stream
        self.input_stream = LegoInputStream(self.config, self.board, usestream=self.used_stream)

        # Initialize ROI as a black RGB-image
        region_of_interest = np.zeros((self.config.get("resolution", "height"),
                                       self.config.get("resolution", "width"), CHANNELS_NUMBER), np.uint8)

        logger.info("initialized lego input stream")

        try:

            # main loop which handles each frame
            while not self.output_stream.update(self.program_stage):

                # get the next frame
                depth_image_3d, color_image = self.input_stream.get_frame()

                # FIXME: fix the method and use it
                # Analyze only objects on the board / table
                clipped_color_image = self.board_detector.clip_board(color_image, depth_image_3d)

                # Add some additional information to the debug window
                color_image_debug = color_image.copy()
                self.output_stream.add_debug_information(color_image_debug)

                # always write the current frame to the board detection channel
                self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_BOARD_DETECTION, color_image_debug)

                # call different functions depending on program state
                if self.program_stage == ProgramStage.WHITE_BALANCE:
                    self.white_balance(color_image)

                elif self.program_stage == ProgramStage.FIND_CORNERS:
                    self.detect_corners(color_image)

                elif self.program_stage == ProgramStage.LEGO_DETECTION:
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
            self.program_stage = self.program_stage.next()

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

            # Use distance to set possible lego brick size
            logger.debug("Calculate possible lego brick size")
            # TODO: test it with different distances
            self.shape_detector.calculate_possible_lego_dimensions(self.board.distance)

            logger.debug("Used threshold for qr-codes -> {}".format(self.board.threshold_qrcode))
            self.output_stream.set_active_channel(LegoOutputChannel.CHANNEL_ROI)
            self.program_stage = self.program_stage.next()

        # use different thresholds for board detection
        self.board_detector.adjust_threshold_qrcode()

    def do_lego_detection(self, region_of_interest, color_image):
        # If the board is detected take only the region
        # of interest and start lego bricks detection

        # Take only the region of interest from the color image
        region_of_interest = self.board_detector.rectify_image(region_of_interest, color_image)
        region_of_interest_debug = region_of_interest.copy()

        # Initialize legos brick properties list
        potential_lego_bricks_list = []

        # detect contours in area of interest
        contours = self.shape_detector.detect_contours(region_of_interest)

        # Loop over the contours
        for contour in contours:

            # Check if the contour is a lego brick candidate (shape and color can be detected)
            brick_candidate = self.shape_detector.detect_lego_brick(contour, region_of_interest)

            if brick_candidate:
                # Update the properties list of all potential lego bricks which are found in the frame
                potential_lego_bricks_list.append(brick_candidate)

                # mark potential lego brick contours
                LegoOutputStream.mark_candidates(region_of_interest_debug, contour)

        # Compute tracked lego bricks dictionary
        # using the centroid tracker and set of properties
        tracked_lego_bricks = self.tracker.update(potential_lego_bricks_list)

        # Loop over the tracked objects and label them in the stream
        for tracked_lego_brick in tracked_lego_bricks:
            LegoOutputStream.labeling(region_of_interest_debug, tracked_lego_brick)

        # write current frame to the stream output
        self.output_stream.write_to_file(region_of_interest_debug)

        # Render shape detection images
        self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_ROI, region_of_interest_debug)


# execute the main class  ' TODO: meaningful rename
if __name__ == '__main__':
    main = LegoLab()
    main.run()
