
# Used pyrealsense2 on License: Apache 2.0.
import pyrealsense2 as rs  # FIXME: CG: this currently requires python 3.6
import logging
import numpy as np
import config

# enable logger
logger = logging.getLogger(__name__)


class LegoInputStream:

    # The configuration instance of the realsense camera
    realsense_config = None
    pipeline = None
    depth_scale = None

    # Initialize squared board size and middle of the board
    middle_x = config.WIDTH//2
    middle_y = config.HEIGHT//2

    # intermediate storage of actual frames
    color_frame = None
    aligned_depth_frame = None

# initialize the input stream (from live camera or bag file)
    def __init__(self, usestream=None):

        self.pipeline = rs.pipeline()
        self.realsense_config = rs.config()

        # FIXME: missing frames when using videostream or too slow processing
        # https://github.com/IntelRealSense/librealsense/issues/2216
        # Use recorded depth and color streams and its configuration
        if usestream is not None:
            rs.config.enable_device_from_file(self.realsense_config, usestream)
            self.realsense_config.enable_all_streams()

        # Configure depth and color streams
        else:
            self.realsense_config.enable_stream(rs.stream.depth, config.WIDTH, config.HEIGHT, rs.format.z16, 30)
            self.realsense_config.enable_stream(rs.stream.color, config.WIDTH, config.HEIGHT, rs.format.bgr8, 30)

            # Create alignment primitive with color as its target stream:
        self.alignment_stream = rs.align(rs.stream.color)

        # Start streaming
        # TODO: optionally rename variable to a more speaking one
        self.profile = self.pipeline.start(self.realsense_config)

        # Getting the depth sensor's depth scale
        depth_sensor = self.profile.get_device().first_depth_sensor()
        self.depth_scale = depth_sensor.get_depth_scale()
        logger.debug("Depth Scale is: {}".format(self.depth_scale))

    def get_frame(self):

        # Wait for depth and color frames
        frames = self.pipeline.wait_for_frames()

        # Align the depth frame to color frame
        aligned_frames = self.alignment_stream.process(frames)

        # Get aligned frames (depth images)
        self.aligned_depth_frame = aligned_frames.get_depth_frame()
        self.color_frame = aligned_frames.get_color_frame()

        # New frame log information
        logger.debug("!! new frame started")

        # Validate that both frames are valid
        if self.aligned_depth_frame and self.color_frame:
            # Convert images to numpy arrays
            depth_image = np.asanyarray(self.aligned_depth_frame.get_data())
            color_image = np.asanyarray(self.color_frame.get_data())

            # TODO: automatically change contrast!
            #color_image = cv2.convertScaleAbs(color_image, 2.2, 2)
            #cv2.imshow("mask", color_image)

            # Change background regarding clip_dist to black
            # Depth image is 1 channel, color is 3 channels
            depth_image_3d = np.dstack((depth_image, depth_image, depth_image))

            return depth_image_3d, color_image

        else:
            return None, None

    def get_distance_to_table(self):
        logger.debug("board detected: {}".format(all_board_corners_found))
        clipping_distance = self.aligned_depth_frame.get_distance(self.middle_x, self.middle_y) / self.depth_scale
        logger.debug("Distance to the table is: {}".format(clipping_distance))

        return clipping_distance

    def close(self):
        # Stop streaming
        self.pipeline.stop()
