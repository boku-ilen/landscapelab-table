
# TODO: optimization possibilities:
# detect inner corners of markers to exclude the QR-Code-markers from analysis
# temporal filtering (IIR filter) to remove "holes" (depth=0), hole-filling
# edge-preserving filtering to smooth the depth noise
# changing the depth step-size
# IR pattern removal

# Used pyrealsense2 on License: Apache 2.0.

from builtins import staticmethod
import pyrealsense2 as rs  # TODO: ship a binary build
import numpy as np
import cv2  # TODO: fix the requirements.txt or provide library
import colorsys # TODO: remove from requirements
import logging.config
import time
import argparse
import pyzbar.pyzbar as pyzbar  # TODO: add to requirements.txt
from BoardDetection.BoardDetector import BoardDetector
from ServerCommunication.ServerCommunication import ServerCommunication
from Tracking.Tracker import Tracker
#from Tracking.MyTracker import MyTracker

# TODO: move some other variables to config?
# Global variables
import config

# configure logging
logger = logging.getLogger(__name__)
try:
    # TODO: Set configurations
    logging.config.fileConfig('logging.conf')
except:
    logging.basicConfig(level=logging.INFO)
    logging.info("Could not initialize: logging.conf not found or misconfigured")


# Max RGB resolution: 1920 x 1080 at 30 fps, depth: up to 1280 x 720, up to 90 fps
# For resolution 1280x720 and distance ~1 meter a short side of lego piece has ~14 px length
WIDTH = int(1280)
HEIGHT = int(720)
# Side of lego piece rotated bounding box  # TODO: automate
MIN_ROTATED_LENGTH = 10
MAX_ROTATED_LENGTH = 35
MIN_AREA = 70
# Objects in greater distance to the board than (1 +- CLIP) * x will be excluded from processing
CLIP = 0.1
# Aspect ratio for square and rectangle
MIN_SQ = 0.7
MAX_SQ = 1.35
MIN_REC = 0.2
MAX_REC = 2.5
# TODO: use only lower, upper arrays
# Accepted HSV colors
BLUE_MIN = (0.53, 0.33, 105)
BLUE_MAX = (0.65, 1, 255)
RED_MIN = (0.92, 0.40, 140)
RED_MAX = (1, 1, 255)
# yellow mask
lower_yellow = np.array([10, 100, 100])
upper_yellow = np.array([20, 255, 200])
# dark green mask
lower_green = np.array([55, 50, 50])
upper_green = np.array([95, 255, 255])
# blue mask
lower_blue = np.array([95, 150, 50])
upper_blue = np.array([150, 255, 180])
# lower red mask (0-10)
lower_red1 = np.array([0, 120, 120])
upper_red1 = np.array([10, 255, 255])
# upper red mask (170-180)
lower_red2 = np.array([170, 50, 120])
upper_red2 = np.array([180, 255, 255])


class ShapeDetector:

    # The centroid tracker instance
    centroid_tracker = None

    pipeline = None

    # The configuration instance of the realsense camera
    realsense_config = None

    depth_scale = None

    # Threshold for finding QR-Codes
    # To change the threshold use an optional parameter
    threshold_qrcode = None

    # FIXME: make this an optional parameter using argparse std library
    def __init__(self):

        self.pipeline = rs.pipeline()
        self.realsense_config = rs.config()

        parser = argparse.ArgumentParser()
        parser.add_argument("--threshold", type=int, default=140,
                            help="set the threshold for black-white image to recognize qr-codes")
        parser.add_argument("--usestream", help="path and name of the file with saved .bag stream")
        parser_arguments = parser.parse_args()

        if parser_arguments.threshold is not None:
            self.threshold_qrcode = parser_arguments.threshold

        # FIXME: missing frames when using videostream or too slow processing
        # https://github.com/IntelRealSense/librealsense/issues/2216
        # Use recorded depth and color streams and its configuration
        if parser_arguments.usestream is not None:
            rs.config.enable_device_from_file(self.realsense_config, parser_arguments.usestream)
            self.realsense_config.enable_all_streams()

        # Configure depth and color streams
        else:
            self.realsense_config.enable_stream(rs.stream.depth, WIDTH, HEIGHT, rs.format.z16, 30)
            self.realsense_config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, 30)

        # Create alignment primitive with color as its target stream:
        self.alignment_stream = rs.align(rs.stream.color)

        # Start streaming
        # TODO: optionally rename variable to a more speaking one
        self.profile = self.pipeline.start(self.realsense_config)

        # Getting the depth sensor's depth scale
        depth_sensor = self.profile.get_device().first_depth_sensor()
        self.depth_scale = depth_sensor.get_depth_scale()
        logger.debug("Depth Scale is: {}".format(self.depth_scale))

        # Initialize board detection
        self.board_detector = BoardDetector()
        self.board_size_height = None
        self.board_size_width = None

        # Initialize server communication class
        self.server = ServerCommunication()

        # Initialize the centroid tracker
        self.centroid_tracker = Tracker(self.server)
        # centroid_tracker = MyTracker()

    # Check if the contour is a lego brick
    # TODO: remove frame if nothing to draw anymore
    def detect_lego_brick(self, contour, frame, mask_blue, mask_red, mask_green):

        # Initialize the contour name and approximate the contour
        # with Douglas-Peucker algorithm
        contour_name = "shape"
        color_name = "wrongColor"
        epsilon = 0.1 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the contour has 4 vertices
        if len(approx) == 4:

            # Compute the bounding box of the contour
            # (x, y, w, h) = cv2.boundingRect(approx)
            # bbox = (x, y, w, h)
            # Draw a blue bounding box (for testing purposes)
            # cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # Compute contour moments, which include area,
            # its centroid, and information about its orientation
            moments_dict = cv2.moments(contour)

            # Compute the centroid of the contour (cX, cY)
            if moments_dict["m00"] != 0:
                centroid_x = int((moments_dict["m10"] / moments_dict["m00"]))
                centroid_y = int((moments_dict["m01"] / moments_dict["m00"]))

                # Check color of the lego brick (currently only red, blue and green accepted)
                if mask_blue[centroid_y, centroid_x] == 255:
                    color_name = "blue"
                elif mask_red[centroid_y, centroid_x] == 255:
                    color_name = "red"
                elif mask_green[centroid_y, centroid_x] == 255:
                    color_name = "green"

                # TODO: remove if the above method is sufficient (masks/lower, upper arrays)
                if color_name == "wrongColor":
                    color_name = self.check_color(centroid_x, centroid_y, frame)

                # TODO: set color using mask
                # Eliminate wrong colors contours
                if color_name == "wrongColor":
                    logger.debug("Don't draw -> wrong color")

                # Eliminate very small contours
                elif cv2.contourArea(contour) < MIN_AREA:
                    logger.debug("Don't draw -> area too small")

                else:

                    # Compute the rotated bounding box
                    rect = cv2.minAreaRect(contour)
                    rotated_bbox = np.int0(cv2.boxPoints(rect))

                    # Draw red contours for all found contours (for testing purposes)
                    # cv2.drawContours(frame, [rotated_bbox], 0, (0, 0, 255), 2)

                    contour_name = self.check_if_square(rotated_bbox)

                    logger.debug("Draw contour:\n Center coordinates: {}, {}\n Contour area: {}".
                                 format(centroid_x, centroid_y, cv2.contourArea(contour)))

            # return contour name, its centroid and color
            return contour_name, centroid_x, centroid_y, color_name

        # return contour name == "shape" centroid = 0,0, color == "wrongColor"
        return contour_name, 0, 0, color_name

    # Check if the contour has a lego brick shape: square or rectangle
    def check_if_square(self, rotated_bbox):

        # Compute the aspect ratio of the two lengths
        # Is set to 0, if the size of lego was not correct
        aspect_ratio = self.calculate_sides_ratio(rotated_bbox)

        contour_name = "shape"
        if aspect_ratio == 0:
            return contour_name

        # Check if aspect ratio is near 1:1
        if MIN_SQ <= aspect_ratio <= MAX_SQ:
            contour_name = "square"
            logger.debug("Square ratio: {}".format(aspect_ratio))

        # Check if aspect ratio is near 2:1
        elif MIN_REC < aspect_ratio < MAX_REC:
            contour_name = "rectangle"
            logger.debug("Rectangle ratio: {}".format(aspect_ratio))

        # return contour name
        return contour_name

    # Compute two sides lengths of the contour, which have a common corner
    @staticmethod
    def calculate_sides_ratio(rotated_bbox):

        # Initialize a list for sides lengths of the contour
        sides_lengths_list = []

        # Compute three lengths for three corners of rotated bounding box
        # These are a triangle, a half of bounding box
        for corner in range(3):
            sides_lengths_list.append(np.linalg.norm(rotated_bbox[0] - rotated_bbox[corner + 1]))

        # Delete the highest length value, which is a diagonal of bounding box
        # Only two sides lengths, which have a common corner, are remaining in the array
        rotated_bbox_lengths = np.delete(sides_lengths_list, np.argmax(sides_lengths_list))
        logger.debug("Rotated bbox size: {}".format(rotated_bbox_lengths))

        # Check if the lego brick is not too small/large
        if (MIN_ROTATED_LENGTH > rotated_bbox_lengths[0] > MAX_ROTATED_LENGTH) \
                | (MIN_ROTATED_LENGTH > rotated_bbox_lengths[1] > MAX_ROTATED_LENGTH):
            logger.debug("Don't draw -> wrong size")
            return 0

        # Compute the aspect ratio of the two lengths
        ratio = int(rotated_bbox_lengths[0]) / int(rotated_bbox_lengths[1])

        # Return the aspect ratio of two sides lengths of the rotated bounding box
        return ratio

    # Compute the color name of the found lego brick
    @staticmethod
    def check_color(x, y, color_image):

        # Calculate the mean color (RGB) in the middle of the found lego brick
        color = cv2.mean(color_image[y:y+4, x:x+4])

        # Change color in RGB to HSV
        color_hsv = colorsys.rgb_to_hsv(color[2], color[1], color[0])
        logger.debug("HSV: {}".format(color_hsv))

        # Initialize the color name
        color_name = "wrongColor"

        # Check if the color is red
        if RED_MIN[0] <= color_hsv[0] <= RED_MAX[0] \
                and RED_MIN[1] <= color_hsv[1] <= RED_MAX[1]\
                and RED_MIN[2] <= color_hsv[2] <= RED_MAX[2]:
            color_name = "red"

        # Check if the color is blue
        elif BLUE_MIN[0] <= color_hsv[0] <= BLUE_MAX[0]\
                and BLUE_MIN[1] <= color_hsv[1] <= BLUE_MAX[1]\
                and BLUE_MIN[2] <= color_hsv[2] <= BLUE_MAX[2]:
            color_name = "blue"

        # Return the color name
        return color_name

    # Run lego bricks detection and tracking code
    def run(self, record_video=False):

        # Define the codec and create VideoWriter object. The output is stored in .avi file.
        # Define the fps to be equal to 10. Also frame size is passed.
        video_handler = None
        if record_video:
            video_handler = cv2.VideoWriter(config.video_output_name, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                            10, (int(WIDTH), int(HEIGHT)))

        # Initialize the clipping distance
        clip_dist = 0

        # Initialize board detection flag
        all_board_corners_found = False

        # Initialize squared board size and middle of the board
        middle_x = int(WIDTH/2)
        middle_y = int(HEIGHT/2)

        try:

            # Run main loop with video frames
            while True:

                # Initialize a timestamp
                t0 = time.time()

                # Wait for depth and color frames
                frames = self.pipeline.wait_for_frames()

                # Align the depth frame to color frame
                aligned_frames = self.alignment_stream.process(frames)

                # Get aligned frames (depth images)
                aligned_depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()

                # New frame log information
                logger.debug("!! new frame started at {}".format(t0))

                # Validate that both frames are valid
                if not aligned_depth_frame or not color_frame:
                    continue

                # Convert images to numpy arrays
                depth_image = np.asanyarray(aligned_depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())

                # Change background regarding clip_dist to black
                # Depth image is 1 channel, color is 3 channels
                depth_image_3d = np.dstack((depth_image, depth_image, depth_image))

                # TODO: find a working pythonic way
                clipped_color_image = np.where(
                    (depth_image_3d > clip_dist * (1 + CLIP)) | (depth_image_3d < clip_dist * (1 - CLIP)), 0,
                    color_image)
                # not working properly
                # clipped_color_image = np.where((depth_image_3d > clip_dist * (1 + CLIP)).all()
                #                               or (depth_image_3d < clip_dist * (1 - CLIP)).all(),
                #                               0, color_image)
                cv2.imshow('Clipped_color', clipped_color_image)

                # Set ROI as the color_image to set the same size
                region_of_interest = color_image

                # TODO: automaticaly change contrast!
                #color_image = cv2.convertScaleAbs(color_image, 2.2, 2)
                #cv2.imshow("mask", color_image)

                # Detect the board using qr-codes polygon data saved in the array
                # -> self.board_detector.all_codes_polygons_points
                if not all_board_corners_found:

                    # Decode QR or Bar-Codes
                    # Convert to black and white to find QR-Codes
                    # Threshold image to white in black

                    mask = cv2.inRange(color_image, (0, 0, 0),
                                       (self.threshold_qrcode, self.threshold_qrcode, self.threshold_qrcode))
                    white_in_black = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                    # Invert image it to black in white
                    looking_for_qr_code_image = 255 - white_in_black
                    decoded_codes = pyzbar.decode(looking_for_qr_code_image)

                    # Mark found QR-codes on the color image
                    self.board_detector.display_found_codes(color_image, decoded_codes)

                    # Show mask for finding qr-codes
                    cv2.imshow('finding qr-codes', white_in_black)

                    # Read codes which were decoded in this frame:
                    # save polygons in the array self.board_detector.all_codes_polygons_points
                    # and read metadata
                    self.board_detector.read_codes(decoded_codes)

                    # Find position of board corners
                    all_board_corners_found, board_corners = self.board_detector.detect_board()

                # Show color image
                cv2.imshow('Color', color_image)

                # Get the distance to the board (to the middle of the frame)
                if not clip_dist or not all_board_corners_found:
                    logger.debug("clip_dist_: {}".format(clip_dist))
                    logger.debug("board detected: {}".format(all_board_corners_found))
                    clip_dist = aligned_depth_frame.get_distance(middle_x, middle_y) / self.depth_scale
                    logger.debug("Distance to the table is: {}".format(clip_dist))

                # If map_id and location coordinates are available, compute board coordinates
                if self.board_detector.map_id is not None and self.server.location_coordinates is None:

                    # Get location of the map from the server,
                    # compute board coordinates and save them in config file
                    self.server.compute_board_coordinates(self.board_detector.map_id)

                if all_board_corners_found and clip_dist:

                    # Check if found QR-code markers positions are included in the frame size
                    if all([0, 0] < corners < [color_image.shape[1], color_image.shape[0]]
                           for corners in board_corners):

                        # Eliminate perspective transformations and show only the board
                        rectified_image, self.board_size_height, self.board_size_width = \
                            self.board_detector.rectify(color_image, board_corners)
                        # rectified_image, self.board_size_height, self.board_size_width = \
                            #    self.board_detector.rectify(clipped_color_image, board_corners)
                        config.board_size_height = self.board_size_height
                        config.board_size_width = self.board_size_width

                        # Set ROI to black and add only the rectified board, where objects are searched
                        region_of_interest[0:HEIGHT, 0:WIDTH] = [0, 0, 0]
                        region_of_interest[0:self.board_size_height, 0:self.board_size_width] = rectified_image

                        # TODO: else: include positions in the frame?

                else:
                    logger.debug("No QR-code detector result")
                    region_of_interest[0:HEIGHT, 0:WIDTH] = [0, 0, 0]

                # Show the board (region of interest)
                cv2.imshow('ROI', region_of_interest)
                frame = region_of_interest

                # Set red and blue mask
                frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                # Set red masks and join them
                mask1 = cv2.inRange(frame_hsv, lower_red1, upper_red1)
                mask2 = cv2.inRange(frame_hsv, lower_red2, upper_red2)
                mask_red = mask1 + mask2
                # cv2.imshow("mask_red", mask_red)

                # Set the blue mask
                mask_blue = cv2.inRange(frame_hsv, lower_blue, upper_blue)
                # cv2.imshow("mask_blue", mask_blue)

                # Set the green mask
                mask_green = cv2.inRange(frame_hsv, lower_green, upper_green)

                # Set the yellow mask
                mask_yellow = cv2.inRange(frame_hsv, lower_yellow, upper_yellow)

                # Do some morphological corrections (fill 'holes' in masks)
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                dilation_blue = cv2.dilate(mask_blue, kernel, iterations=1)
                # cv2.imshow("dilation_blue", dilation_blue)
                dilation_red = cv2.dilate(mask_red, kernel, iterations=1)
                # cv2.imshow("dilation_red", dilation_red)
                dilation_green = cv2.dilate(mask_green, kernel, iterations=1)
                # cv2.imshow("dilation_green", dilation_green)
                dilation_yellow = cv2.dilate(mask_yellow, kernel, iterations=1)
                # cv2.imshow("dilation_yellow", dilation_yellow)

                # Add mask with all allowed colors (currently red and blue)
                mask_colors = dilation_red + dilation_blue + dilation_green
                # cv2.imshow("mask_colors", mask_colors)

                thresh = mask_colors

                # Find contours in the thresholded image

                # Retrieve all of the contours without establishing any hierarchical relationships (RETR_LIST)
                _, contours, hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

                # Initialize legos brick properties list and its length
                legos_properties_list = []
                legos_properties_list_length = 0

                # Loop over the contours
                for contour in contours:

                    # Check if the contour is a lego brick
                    # Compute contour name and rotated bounding box of the found contour
                    contour_name, centroid_x, centroid_y, color_name \
                        = self.detect_lego_brick(contour, frame, mask_blue, mask_red, mask_green)

                    # If the contour name is computed (square or rectangle),
                    # it means the contour has a shape, color and size of lego brick
                    if contour_name != "shape":

                        # Draw green lego bricks contours
                        cv2.drawContours(frame, [contour], -1, (0, 255, 0), 3)

                        # TODO: TODO: there should be only one contour for one lego piece! implement in the tracker/lego brick
                        # Skip contour if there are others with almost the same position
                        # for lego_brick in legos_properties_list:
                        #    if centroid_x - 6 < lego_brick[0] < centroid_x + 6 \
                        #            & centroid_y - 6 < lego_brick[1] < centroid_y + 6:
                        #        print("don't save", centroid_x, centroid_y)
                        #        break

                        # Update the properties list of all lego bricks which are found in the frame
                        legos_properties_list.append((centroid_x, centroid_y, contour_name, color_name))
                        legos_properties_list_length += 1

                # Log all objects with properties
                logger.debug("All saved objects with properties:")
                for lego_brick in legos_properties_list:
                    logger.debug(lego_brick)

                # TODO: work with objects
                # Compute tracked lego bricks dictionary
                # using the centroid tracker and set of properties
                tracked_lego_bricks_dict = \
                    self.centroid_tracker.update(legos_properties_list, legos_properties_list_length)

                # Loop over the tracked objects
                for (ID, tracked_lego_brick) in tracked_lego_bricks_dict.items():

                    # Draw green lego bricks IDs
                    text = "ID {}".format(ID)
                    tracked_lego_brick_position = tracked_lego_brick[0][0], tracked_lego_brick[0][1]
                    cv2.putText(frame, text, (tracked_lego_brick[0][0] - 10, tracked_lego_brick[0][1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                    # Draw green lego bricks contour names
                    cv2.putText(frame, tracked_lego_brick[1], tracked_lego_brick_position,
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                    # Draw green lego bricks centroid points
                    cv2.circle(frame, tracked_lego_brick_position, 4, (0, 255, 0), -1)

                    logger.debug("Detection: {}, {}".format(ID, tracked_lego_brick))

                # Write the frame into the file 'output.avi'
                if record_video:
                    video_handler.write(frame)

                # Render shape detection images
                cv2.namedWindow('Shape detection', cv2.WINDOW_AUTOSIZE)
                cv2.imshow('Shape detection', frame)
                key = cv2.waitKey(33)

                # Break with Esc
                if key == 27:
                    break

        finally:
            if record_video:
                video_handler.release()
            # Stop streaming
            self.pipeline.stop()


# Example usage is run if file is executed directly
if __name__ == '__main__':
    my_shape_detector = ShapeDetector()
    my_shape_detector.run()

