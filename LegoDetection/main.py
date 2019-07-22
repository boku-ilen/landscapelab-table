import argparse
import logging.config

from BoardDetector import BoardDetector
from LegoDetection import ShapeDetector
from LegoInputStream import LegoInputStream
from LegoOutputStream import LegoOutputStream, LegoOutputChannel
from ServerCommunication import ServerCommunication
from Tracker import Tracker
from ConfigManager import ConfigManager


# configure logging
logger = logging.getLogger(__name__)
try:
    logging.config.fileConfig('logging.conf')
    logger.info("Logging initialized")
except:
    logging.basicConfig(level=logging.DEBUG)
    logging.info("Could not initialize: logging.conf not found or misconfigured")


# TODO: rename
# this class manages the base workflow and handles the main loop
class Main:

    def __init__(self):

        # Initialize config manager
        self.config = ConfigManager()

        # Parse optional parameters
        # FIXME: CG: parameters have to be handled in the main method?
        parser = argparse.ArgumentParser()
        parser.add_argument("--threshold", type=int,
                            help="set the threshold for black-white image to recognize qr-codes")
        parser.add_argument("--usestream", help="path and name of the file with saved .bag stream")
        parser.add_argument("--ip", help="local ip, if other than localhost")
        parser_arguments = parser.parse_args()

        if parser_arguments.threshold is not None:
            threshold_qrcode = parser_arguments.threshold
        else:
            threshold_qrcode = self.config.get("qr_code", "threshold")

        if parser_arguments.usestream is not None:
            self.used_stream = parser_arguments.usestream
        else:
            self.used_stream = None

        if parser_arguments.ip is not None:
            self.config.set("server", "ip", parser_arguments.ip)

        # FIXME: switched colors in new saved streams, configs?
        # initialize the input and output stream
        self.output_stream = LegoOutputStream()
        self.input_stream = LegoInputStream(usestream=self.used_stream)

        # Initialize board detection
        self.board_detector = BoardDetector(threshold_qrcode, self.output_stream)

        # Initialize server communication class
        self.server = ServerCommunication(self.config, self.board_detector)

        # Initialize the centroid tracker
        self.tracker = Tracker(self.server)

        # initialize the lego detector
        self.shape_detector = ShapeDetector()

    # Run lego bricks detection and tracking code
    def run(self):

        # Initialize the clipping distance
        clip_dist = 0

        # Initialize board detection flag
        all_board_corners_found = False

        # initialize the input stream
        self.input_stream = LegoInputStream(usestream=self.used_stream)

        logger.info("initialized lego input stream")

        try:

            # main loop which handles each frame
            while not self.output_stream.update():

                # get the next frame
                depth_image_3d, color_image = self.input_stream.get_frame()

                # Set ROI as the color_image to set the same size
                region_of_interest = self.board_detector.clip_board(color_image, depth_image_3d)

                # Detect the board using qr-codes polygon data saved in the array
                # -> self.board_detector.all_codes_polygons_points
                if not all_board_corners_found:

                    # Find position of board corners
                    all_board_corners_found, board_corners = self.board_detector.detect_board(color_image)

                # Show color image
                self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_COLOR, color_image)

                # Get the distance to the board (to the middle of the frame)
                # TODO: CG: why is this handled this way?
                if not clip_dist or not all_board_corners_found:
                    clip_dist = self.input_stream.get_distance_to_table()

                # If map_id and location coordinates are available, compute board coordinates
                # FIXME: this has to be abstracted as the implementation may change if the beamer variant is used
                if self.board_detector.map_id is not None and self.server.location_coordinates is None:

                    # Get location of the map from the server,
                    # compute board coordinates and save them in config file
                    self.server.compute_board_coordinates(self.board_detector.map_id)

                # FIXME: why should clip_dist ever be None here?
                if all_board_corners_found and clip_dist:
                    region_of_interest = self.board_detector.rectify_image(region_of_interest, color_image)

                else:
                    logger.debug("No QR-code detector result")
                    height = self.config.get("resolution", "height")
                    width = self.config.get("resolution", "width")
                    region_of_interest[0:height, 0:width] = [0, 0, 0]

                # Show the board (region of interest)
                self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_ROI, region_of_interest)

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
                self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_SHAPE_DETECTION, region_of_interest)

        finally:
            # handle the output stream correctly
            self.output_stream.close()

            # make sure the stream ends correctly
            self.input_stream.close()


# execute the main class  ' TODO: meaningful rename
if __name__ == '__main__':
    main = Main()
    main.run()
