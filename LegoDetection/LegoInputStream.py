
# Used pyrealsense2 on License: Apache 2.0.
import pyrealsense2 as rs  # FIXME: CG: this currently requires python 3.6
import logging
import numpy as np

# enable logger
logger = logging.getLogger(__name__)


class LegoInputStream:

    # The configuration instance of the realsense camera
    realsense_config = None
    pipeline = None
    depth_scale = None

    # Initialize the resolution
    width = None
    height = None

    # intermediate storage of actual frames
    color_frame = None
    aligned_depth_frame = None

    # initialize the input stream (from live camera or bag file)
    def __init__(self, config, usestream=None):

        self.pipeline = rs.pipeline()
        self.realsense_config = rs.config()

        # Get the resolution from config file
        self.width = config.get("resolution", "width")
        self.height = config.get("resolution", "height")

        # FIXME: missing frames when using videostream or too slow processing
        # https://github.com/IntelRealSense/librealsense/issues/2216

        # Use recorded depth and color streams and its configuration
        # If problems with colors occur, check bgr/rgb channels configurations
        if usestream is not None:
            rs.config.enable_device_from_file(self.realsense_config, usestream)
            self.realsense_config.enable_all_streams()

        # Configure depth and color streams
        else:
            self.realsense_config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, 30)
            self.realsense_config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, 30)

            # Create alignment primitive with color as its target stream:
        self.alignment_stream = rs.align(rs.stream.color)

        # Start streaming
        # TODO: optionally rename variable to a more speaking one
        # FIXME: program ends here without further message
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
        logger.info("!! new frame started")

        # Validate that both frames are valid
        if self.aligned_depth_frame and self.color_frame:
            # Convert images to numpy arrays
            depth_image = np.asanyarray(self.aligned_depth_frame.get_data())
            color_image = np.asanyarray(self.color_frame.get_data())

            # TODO: automatically change contrast!
            # color_image = cv2.convertScaleAbs(color_image, 2.2, 2)
            # cv2.imshow("mask", color_image)

            # Change background regarding clip_dist to black
            # Depth image is 1 channel, color is 3 channels
            depth_image_3d = np.dstack((depth_image, depth_image, depth_image))

            return depth_image_3d, color_image

        else:
            return None, None

    def get_distance_to_table(self):
        board_distance = self.aligned_depth_frame.get_distance(int(self.width/2), int(self.height/2)) / self.depth_scale

        return board_distance

    def close(self):
        # Stop streaming
        self.pipeline.stop()
