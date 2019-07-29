import logging.config
import numpy as np

from BoardDetector import BoardDetector
from LegoDetection import ShapeDetector
from LegoInputStream import LegoInputStream
from LegoOutputStream import LegoOutputStream, LegoOutputChannel
from LegoUI.MapHandler import MapHandler
from LegoUI.UIElements.UISetup import setup_ui
from ServerCommunication import ServerCommunication
from Tracker import Tracker
from ConfigManager import ConfigManager
from ParameterManager import ParameterManager
from LegoUI.ListenerThread import ListenerThread


# configure logging
logger = logging.getLogger(__name__)
try:
    logging.config.fileConfig('logging.conf')
    logger.info("Logging initialized")
except:
    logging.basicConfig(level=logging.INFO)
    logging.info("Could not initialize: logging.conf not found or misconfigured")


# TODO: rename
# this class manages the base workflow and handles the main loop
class Main:

    def __init__(self):

        # Initialize config manager
        self.config = ConfigManager()

        # Initialize parameter manager and parse arguments
        self.parser = ParameterManager(self.config)
        self.used_stream = self.parser.used_stream

        # Initialize server communication class
        self.server = ServerCommunication(self.config)

        # initialize map handler and ui
        self.map_handler = MapHandler(self.config)
        ui_root = setup_ui(self.map_handler.action_map)

        # Initialize the centroid tracker
        self.tracker = Tracker(self.config, self.server, ui_root)

        # initialize the input and output stream
        self.output_stream = LegoOutputStream(self.map_handler, ui_root, self.tracker, self.config)
        self.input_stream = LegoInputStream(self.config, usestream=self.used_stream)

        # Initialize board detection
        self.board_detector = BoardDetector(self.config, self.config.get("qr_code", "threshold"), self.output_stream)

        # Initialize the QGIS listener Thread
        self.listener_thread = ListenerThread(self.config, self.map_handler)
        self.listener_thread.start()

        # initialize the lego detector
        self.shape_detector = ShapeDetector()

    # Run lego bricks detection and tracking code
    def run(self):

        # Initialize board detection flag
        all_board_corners_found = False

        # initialize the input stream
        self.input_stream = LegoInputStream(self.config, usestream=self.used_stream)

        # Initialize ROI as a black RGB-image
        region_of_interest = np.zeros((self.config.get("resolution", "height"),
                                       self.config.get("resolution", "width"), 3), np.uint8)

        logger.info("initialized lego input stream")

        try:

            # main loop which handles each frame
            while not self.output_stream.update():

                # get the next frame
                depth_image_3d, color_image = self.input_stream.get_frame()

                # FIXME: fix the method and use it
                # Analyze only objects on the board / table
                clipped_color_image = self.board_detector.clip_board(color_image, depth_image_3d)

                # Detect the board using qr-codes polygon data saved in the array
                # -> self.board_detector.all_codes_polygons_points
                if not all_board_corners_found:

                    logger.debug("No QR-code detector result")
                    # TODO: use distance to set possible lego brick size
                    logger.debug("Distance to the board is: {}".format(self.input_stream.get_distance_to_table()))

                    # Find position of board corners
                    all_board_corners_found, board_corners = self.board_detector.detect_board(color_image)

                    # Show the whole color image until the board detected
                    self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_COLOR_DETECTION, color_image)

                # If the board is detected take only the region
                # of interest and start lego bricks detection
                else:

                    # Take only the region of interest from the color image
                    region_of_interest = self.board_detector.rectify_image(region_of_interest, color_image)

                    # Initialize legos brick properties list
                    potential_lego_bricks_list = []

                    # detect contours in area of interest
                    contours, color_masks = self.shape_detector.detect_contours(region_of_interest)

                    # Loop over the contours
                    for contour in contours:

                        # Check if the contour is a lego brick candidate (shape and color can be detected)
                        brick_candidate = self.shape_detector.detect_lego_brick(contour, region_of_interest, color_masks)

                        if brick_candidate:
                            # Update the properties list of all potential lego bricks which are found in the frame
                            potential_lego_bricks_list.append(brick_candidate)

                            # mark potential lego brick contours
                            LegoOutputStream.mark_candidates(region_of_interest, contour)

                    # Compute tracked lego bricks dictionary
                    # using the centroid tracker and set of properties
                    tracked_lego_bricks = self.tracker.update(potential_lego_bricks_list)

                    # Loop over the tracked objects and label them in the stream
                    for tracked_lego_brick in tracked_lego_bricks:
                        LegoOutputStream.labeling(region_of_interest, tracked_lego_brick)

                    # write current frame to the stream output
                    self.output_stream.write_to_file(region_of_interest)

                    # Render shape detection images
                    if all_board_corners_found:
                        self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_COLOR_DETECTION, region_of_interest)

        finally:
            # handle the output stream correctly
            self.output_stream.close()

            # make sure the stream ends correctly
            self.input_stream.close()

            self.map_handler.end()


# execute the main class  ' TODO: meaningful rename
if __name__ == '__main__':
    main = Main()
    main.run()
