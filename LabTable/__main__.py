import json
import logging.config
import numpy as np

from .Model.ProgramStage import ProgramStage, CurrentProgramStage
from .BrickDetection.BoardDetector import BoardDetector
from .BrickDetection.ShapeDetector import ShapeDetector
from .InputStream.TableInputStream import TableInputStream
from .TableOutputStream import TableOutputStream, TableOutputChannel
from .BrickDetection.Tracker import Tracker
from .Configurator import Configurator
from .ParameterManager import ParameterManager

# configure logging
logger = logging.getLogger(__name__)

try:
    fp = open("logging.json")
    config = json.load(fp)
    fp.close()

    logging.config.dictConfig(config)
    # logging.config.fileConfig('logging.conf', disable_existing_loggers=True)
    logger.info("Logging initialized")

except Exception as e:
    print("logging could not be initialized. trying fallback.")
    print(e)
    logging.basicConfig(level=logging.INFO)
    logging.info("Could not initialize: logging.conf not found or misconfigured")

# Number of RGB channels in
# region of interest image
CHANNELS_NUMBER = 3


# this class manages the base workflow and handles the main loop
class LabTable:

    def __init__(self):

        # Initialize config manager
        self.config = Configurator()
        TableOutputStream.set_screen_config_info(self.config)

        self.program_stage = CurrentProgramStage()

        # Initialize parameter manager and parse arguments
        self.parser = ParameterManager(self.config)
        self.used_stream = self.parser.used_stream

        # Initialize board detection
        self.board_detector = BoardDetector(self.config)
        self.board = self.board_detector.board

        # Initialize the centroid tracker
        self.tracker = Tracker(self.config)

        # initialize the input and output stream
        self.output_stream = TableOutputStream(self.tracker,
                                               self.config, self.board, self.program_stage)
        self.input_stream = TableInputStream.get_table_input_stream(self.config, self.board, usestream=self.used_stream)

        # initialize the brick detector
        self.shape_detector = ShapeDetector(self.config, self.output_stream)

    # Run bricks detection and tracking code
    def run(self):

        # Initialize ROI as a black RGB-image
        region_of_interest = np.zeros((self.config.get("video_resolution", "height"),
                                       self.config.get("video_resolution", "width"), CHANNELS_NUMBER), np.uint8)

        if self.input_stream and self.input_stream.is_initialized():
            logger.info("initialized input stream")

            try:

                # main loop which handles each frame
                while not self.output_stream.update(self.program_stage):

                    # get the next frame
                    depth_image_3d, color_image = self.input_stream.get_frame()

                    # Add some additional information to the debug window
                    color_image_debug = color_image.copy()

                    # always write the current frame to the board detection channel
                    self.output_stream.write_to_channel(TableOutputChannel.CHANNEL_BOARD_DETECTION, color_image_debug)

                    # call different functions depending on program state
                    if self.program_stage.current_stage == ProgramStage.WHITE_BALANCE:

                        # calculate the average white image
                        if self.board_detector.compute_background(color_image):
                            # switch to next stage if finished
                            self.program_stage.next()

                    # detect the corners by finding the qr-codes
                    elif self.program_stage.current_stage == ProgramStage.FIND_CORNERS:

                        # Compute distance to the board
                        self.input_stream.get_distance_to_board()

                        # Find position of board corners
                        all_board_corners_found = self.board_detector.detect_board(color_image, self.output_stream)

                        # if all corners were found change channel and start next stage
                        if all_board_corners_found:
                            # Use distance to set possible brick size
                            self.shape_detector.calculate_possible_brick_dimensions(self.board.distance)

                            self.output_stream.set_active_channel(TableOutputChannel.CHANNEL_ROI)
                            self.program_stage.next()

                    # do the general brick detection (for internal or external ProgramStage)
                    else:
                        self.do_brick_detection(region_of_interest, color_image)

            except Exception as e:
                logger.error("closing because encountered a problem: {}".format(e))
                logger.exception(e)

        # handle the output stream correctly
        if self.output_stream:
            self.output_stream.close()

        # make sure the stream ends correctly
        if self.input_stream:
            self.input_stream.close()

    def do_brick_detection(self, region_of_interest, color_image):
        # If the board is detected take only the region
        # of interest and start brick detection

        # Take only the region of interest from the color image
        region_of_interest = self.board_detector.rectify_image(region_of_interest, color_image)
        region_of_interest_debug = region_of_interest.copy()

        # Initialize brick properties list
        potential_bricks_list = []

        # detect contours in area of interest
        contours = self.shape_detector.detect_contours(region_of_interest)

        # Loop over the contours
        for contour in contours:

            # Check if the contour is a brick candidate (shape and color can be detected)
            brick_candidate = self.shape_detector.detect_brick(contour, region_of_interest)

            if brick_candidate:
                # Update the properties list of all potential bricks which are found in the frame
                potential_bricks_list.append(brick_candidate)

                # mark potential brick contours
                TableOutputStream.mark_candidates(region_of_interest_debug, contour)

        # Compute tracked bricks dictionary using the centroid tracker and set of properties
        # Mark stored bricks virtual
        tracked_bricks = self.tracker.update(potential_bricks_list, self.program_stage.current_stage)

        # Loop over the tracked objects and label them in the stream
        for tracked_brick in tracked_bricks:
            TableOutputStream.labeling(region_of_interest_debug, tracked_brick)

        # write current frame to the stream output
        self.output_stream.write_to_file(region_of_interest_debug)

        # Render shape detection images
        self.output_stream.write_to_channel(TableOutputChannel.CHANNEL_ROI, region_of_interest_debug)

    def get_program_stage(self) -> ProgramStage:
        return self.program_stage.current_stage


# execute the main class  ' TODO: meaningful rename
if __name__ == '__main__':
    main = LabTable()
    main.run()
