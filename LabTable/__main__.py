import json
import logging.config
import time

import cv2
import numpy as np
from cv2 import Mat

from LabTable.DrawingRecognition.DrawingDetector import average_mats, mark_drawings
from .Model.ProgramStage import ProgramStage, CurrentProgramStage
from .BrickDetection.BoardDetector import BoardDetector
from .BrickDetection.ShapeDetector import ShapeDetector
from .InputStream.TableInputStream import TableInputStream
from .TableOutputStream import TableOutputStream, TableOutputChannel
from .BrickDetection.Tracker import Tracker
from .BrickHandling.WebSocket import WebSocketBrickHandler
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
        self.tracker = Tracker(self.config, WebSocketBrickHandler())

        # initialize the input and output stream
        self.output_stream = TableOutputStream(self.tracker,
                                               self.config, self.board, self.program_stage, self.board_detector)
        self.input_stream = TableInputStream.get_table_input_stream(self.config, self.board, usestream=self.used_stream)

        # initialize the brick detector
        self.shape_detector = ShapeDetector(self.config, self.output_stream)
        self.output_stream.shape_detector = self.shape_detector
        self.pre_drawing_stage = self.program_stage.current_stage

        # number of frames to average for drawing capture
        self.drawing_num_frames = self.config.get("drawing", "frame_average_count")

        # number of frames to skip before averaging for drawing capture
        self.drawing_num_discard = self.config.get("drawing", "frame_delay_count")
        self.frame_times = []

    # Run bricks detection and tracking code
    def run(self, once=False):

        # Initialize ROI as a black RGB-image
        region_of_interest = np.zeros((self.config.get("video_resolution", "height"),
                                       self.config.get("video_resolution", "width"), CHANNELS_NUMBER), np.uint8)
        exit_flag = False
        if self.input_stream and self.input_stream.is_initialized():
            if not once:
                logger.info("initialized input stream")

            try:
                drawing_buffer = []
                # main loop which handles each frame
                while not exit_flag:
                    if self.output_stream.update(self.program_stage):
                        break

                    # get the next frame
                    depth_image_3d, color_image = self.input_stream.get_frame()
                    if color_image is None:
                        if cv2.waitKeyEx() == 27:
                            break
                        continue

                    tick = time.perf_counter_ns()
                    # Add some additional information to the debug window
                    #color_image_debug = color_image #color_image.copy()

                    # always write the current frame to the board detection channel
                    #self.output_stream.write_to_channel(TableOutputChannel.CHANNEL_BOARD_DETECTION, color_image_debug)

                    # call different functions depending on program state
                    if self.program_stage.current_stage == ProgramStage.FIND_CORNERS:

                        logger.info("running board detection")
                        # Find position of board corners
                        all_board_corners_found = self.board_detector.detect_board(color_image)

                        # if all corners were found change channel and start next stage
                        if all_board_corners_found:
                            # Use distance to set possible brick size

                            self.shape_detector.calculate_possible_brick_dimensions(self.board_detector.projection_height, self.board.height)

                            self.output_stream.set_active_channel(TableOutputChannel.CHANNEL_ROI)
                            self.program_stage.next()
                    # drawing capture stage: take frames until ready to average and mark
                    elif self.program_stage.current_stage == ProgramStage.DRAWING_CAPTURE:
                        drawing_buffer.append((self.board_detector.rectify(color_image)))
                        if len(drawing_buffer) >= self.drawing_num_frames + self.drawing_num_discard:
                            drawing_buffer = drawing_buffer[int(self.drawing_num_discard):]
                            draw_base = average_mats(drawing_buffer)
                            sample_pts = self.tracker.brick_handler.queued_drawing_samples()
                            logger.info("marking")
                            drawings, ids, bounds, resolution = mark_drawings(draw_base, len(sample_pts), sample_pts)
                            drawing_buffer.clear()
                            self.tracker.brick_handler.handle_processed_drawing(drawings, ids, bounds, resolution)
                            self.program_stage.current_stage = self.pre_drawing_stage
                    # do the general brick detection (for internal or external ProgramStage)
                    else:
                        # normal brick detection, then switch to capture if requested
                        self.pre_drawing_stage = self.program_stage.current_stage
                        self.do_brick_detection(color_image)
                        if self.tracker.brick_handler.queued_drawing_samples() is not None:
                            self.program_stage.current_stage = ProgramStage.DRAWING_CAPTURE
                    if once:
                        exit_flag = True
                    self.frame_times.append((time.perf_counter_ns() - tick) / 1000000)


            except Exception as e:
                logger.error("closing because encountered a problem: {}".format(e))
                logger.exception(e)

        # handle the output stream correctly
        if self.output_stream and not once:
            self.output_stream.close()

        # make sure the stream ends correctly
        if self.input_stream and not once:
            self.input_stream.close()

        if self.tracker.brick_handler and not once:
            self.tracker.brick_handler.dispose()

    def do_brick_detection(self, color_image):
        # If the board is detected take only the region
        # of interest and start brick detection

        # Take only the region of interest from the color image
        region_of_interest = self.board_detector.rectify(color_image)

        # Initialize brick properties list
        potential_bricks_list = []

        # detect contours in area of interest
        contours = self.shape_detector.detect_contours(region_of_interest)
        candidates = []
        # Loop over the contours
        for contour in contours:

            # Check if the contour is a brick candidate (shape and color can be detected)
            brick_candidate = self.shape_detector.detect_brick(contour, region_of_interest)

            if brick_candidate:
                # Update the properties list of all potential bricks which are found in the frame
                potential_bricks_list.append(brick_candidate)
                # mark in later step to reuse input mat without affecting detection
                candidates.append(contour)

        for contour in candidates:
            # mark potential brick contours
            TableOutputStream.mark_candidates(region_of_interest, contour)

        # Compute tracked bricks dictionary using the centroid tracker and set of properties
        # Mark stored bricks virtual
        tracked_bricks = self.tracker.update(potential_bricks_list, self.program_stage.current_stage)

        # Loop over the tracked objects and label them in the stream
        for tracked_brick in tracked_bricks:
            TableOutputStream.labeling(region_of_interest, tracked_brick)

        # write current frame to the stream output
        self.output_stream.write_to_file(region_of_interest)

        cv2.putText(region_of_interest, f"{round(sum(self.frame_times[-5:])/5, 2)} ms/frame", (0,128),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
        cv2.putText(region_of_interest, f"threshold {self.shape_detector.sat_threshold}", (0,256),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
        self.frame_times = self.frame_times[-5:]
        # Render shape detection images
        self.output_stream.write_to_channel(TableOutputChannel.CHANNEL_ROI, cv2.resize(region_of_interest, (1280, 720)))

    def get_program_stage(self) -> ProgramStage:
        return self.program_stage.current_stage


# execute the main class  ' TODO: meaningful rename
if __name__ == '__main__':
    main = LabTable()
    main.run()
