# TODO: optimization possibilities:
# detect inner corners of markers to exclude the QR-Code-markers from analysis
# temporal filtering (IIR filter) to remove "holes" (depth=0), hole-filling
# edge-preserving filtering to smooth the depth noise
# changing the depth step-size
# IR pattern removal

import logging
from builtins import staticmethod
import cv2  # TODO: fix the requirements.txt or provide library
import numpy as np

from LegoBricks import LegoBrick, LegoShape, LegoColor


# enable logger
logger = logging.getLogger(__name__)

# Aspect ratio for square and rectangle
MIN_SQ = 0.7
MAX_SQ = 1.35
MIN_REC = 0.2
MAX_REC = 2.5
BRICK_LENGTH_BUFFER = 2

# Hue histogram configurations
# Color channel
HUE = [0]
# Histogram size
HIST_SIZE = [181]
# Range
RANGE = [0, 181]

# TODO: make masks configurable ?
# OpenCV supports:
# H-value range (0 to 180)
# S-value range (0 to 255)
# V-value range (0 to 255)
masks_configuration = {
    # TODO: adjust yellow so skin will be excluded
    #LegoColor.YELLOW_BRICK: [
    #    (np.array([10, 100, 100]), np.array([20, 255, 200])),
    #],
    # TODO: adjust green so black will be excluded
    #LegoColor.GREEN_BRICK: [
    #    (np.array([40, 50, 50]), np.array([80, 255, 255])),
    #],
    LegoColor.BLUE_BRICK: [
        (np.array([80, 50, 50]), np.array([140, 255, 255])),
    ],
    LegoColor.RED_BRICK: [
        (np.array([0, 50, 50]), np.array([20, 255, 255])),
        (np.array([160, 50, 50]), np.array([180, 255, 255])),
    ]
}


class ShapeDetector:

    # The centroid tracker instance
    tracker = None

    pipeline = None

    histogram_mask = None

    # Initialize possible lego brick sizes
    min_square_length = None
    max_square_length = None
    min_rectangle_length = None
    max_rectangle_length = None

    min_square_area = None
    max_square_area = None
    min_rectangle_area = None
    max_rectangle_area = None

    def __init__(self, config, output_stream):

        self.config = config
        self.output_stream = output_stream

    # Check if the contour is a lego brick
    # TODO: remove frame if nothing to draw anymore
    def detect_lego_brick(self, contour, frame) -> LegoBrick:

        # Initialize the contour name and approximate the contour
        # with Douglas-Peucker algorithm
        contour_shape: LegoShape = LegoShape.UNKNOWN_SHAPE
        detected_color: LegoColor = LegoColor.UNKNOWN_COLOR
        epsilon = 0.1 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the contour has 4 vertices
        if len(approx) == 4:

            # Compute contour moments, which include area,
            # its centroid, and information about its orientation
            moments_dict = cv2.moments(contour)

            # Compute the centroid of the contour
            if moments_dict["m00"] != 0:
                centroid_x = int((moments_dict["m10"] / moments_dict["m00"]))
                centroid_y = int((moments_dict["m01"] / moments_dict["m00"]))

                # Eliminate too small contours
                if cv2.contourArea(contour) < self.min_square_area:
                    logger.debug("Don't draw -> area too small")

                # Eliminate too large contours
                elif cv2.contourArea(contour) > self.max_rectangle_area:
                    logger.debug("Don't draw -> area too large")

                else:

                    # Check if contour is a rectangle or square
                    contour_shape = self.check_if_square(approx)

                    if contour_shape is LegoShape.UNKNOWN_SHAPE:
                        logger.debug("Don't draw -> unknown shape")
                    else:

                        # Create an empty histogram mask of the frame size
                        if self.histogram_mask is None:
                            self.histogram_mask = np.zeros(frame.shape[:2], np.uint8)

                        # Compute the bounding box of the contour
                        bbox = cv2.boundingRect(approx)

                        # Find the most frequent color (heu value)
                        # in the bounding box
                        detected_color = self.find_most_frequent_hue(bbox, frame)

                        #cv2.drawContours(frame, [approx], 0, (0, 255, 0), 1)

                        # Eliminate wrong colors contours
                        if detected_color == LegoColor.UNKNOWN_COLOR:
                            logger.debug("Don't draw -> unknown color")
                        else:
                            logger.debug("Draw contour:\n Shape: {}\n Color: {}\n "
                                         "Center coordinates: {}, {}\n Contour area: {}".
                                         format(contour_shape, detected_color,
                                                centroid_x, centroid_y, cv2.contourArea(contour)))

                            # return a LegoBrick with the detected parameters
                            return LegoBrick(centroid_x, centroid_y, contour_shape, detected_color)

        return None  # FIXME: CG: we might to differ?

    # Check if the contour has a lego brick shape: square or rectangle
    def check_if_square(self, rotated_bbox) -> LegoShape:

        rotated_bbox_lengths = self.calculate_rotated_bbox_lengths(rotated_bbox)

        # Compute the aspect ratio of the two lengths
        aspect_ratio = int(rotated_bbox_lengths[0]) / int(rotated_bbox_lengths[1])

        # Check if aspect ratio is near 1:1
        if MIN_SQ <= aspect_ratio <= MAX_SQ:

            # Check if sides of the square lego brick are not too short/long
            if not (self.min_square_length < rotated_bbox_lengths[0] < self.max_square_length) \
                    and (self.min_square_length < rotated_bbox_lengths[1] < self.max_square_length):
                logger.debug("Wrong square sides lengths: {}".format(rotated_bbox_lengths))
                return LegoShape.UNKNOWN_SHAPE

            logger.debug("Rotated bbox size: {}".format(rotated_bbox_lengths))
            logger.debug("Square ratio: {}".format(aspect_ratio))
            return LegoShape.SQUARE_BRICK

        # Check if aspect ratio is near 2:1
        elif MIN_REC < aspect_ratio < MAX_REC:

            # Check if sides of the rectangle lego brick are not too short/long
            if not (self.min_rectangle_length < rotated_bbox_lengths[0] < self.max_rectangle_length) \
                    and (self.min_rectangle_length < rotated_bbox_lengths[1] < self.max_rectangle_length):
                logger.debug("Wrong rectangle sides lengths: {}".format(rotated_bbox_lengths))
                return LegoShape.UNKNOWN_SHAPE

            logger.debug("Rotated bbox size: {}".format(rotated_bbox_lengths))
            logger.debug("Rectangle ratio: {}".format(aspect_ratio))
            return LegoShape.RECTANGLE_BRICK

        else:
            return LegoShape.UNKNOWN_SHAPE

    # Compute two sides lengths of the contour, which have a common corner
    @staticmethod
    def calculate_rotated_bbox_lengths(rotated_bbox):

        # Initialize a list for sides lengths of the contour
        sides_lengths_list = []

        # Compute three lengths for three corners of rotated bounding box
        # These are a triangle, a half of bounding box
        for corner in range(3):
            sides_lengths_list.append(np.linalg.norm(rotated_bbox[0] - rotated_bbox[corner + 1]))

        # Delete the highest length value, which is a diagonal of bounding box
        # Only two sides lengths, which have a common corner, are remaining in the array
        rotated_bbox_lengths = np.delete(sides_lengths_list, np.argmax(sides_lengths_list))

        return rotated_bbox_lengths

    @staticmethod
    def detect_contours(frame):

        # Find all edges
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_gray = 255 - frame_gray
        edges = cv2.Canny(frame_gray, 30, 120)

        # Find contours in the edges image
        # Retrieve all of the contours without establishing any hierarchical relationships (RETR_LIST)
        major = cv2.__version__.split('.')[0]
        if major == '3':
            _, contours, hierarchy = cv2.findContours(edges.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, hierarchy = cv2.findContours(edges.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        return contours

    def find_most_frequent_hue(self, bbox, frame):

        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Save dimensions of the bounding box
        (left_x, upper_y, width, height) = bbox

        # Calculate a new bounding box
        # which is 25% of the old one
        # and is placed in its middle
        new_width = int(width / 2)
        new_height = int(height / 2)
        new_left_x = left_x + int(new_width / 2)
        new_upper_y = upper_y + int(new_height / 2)
        new_right_x = new_left_x + new_width
        new_bottom_y = new_upper_y + new_height

        # TODO: maybe make histogram without cv2.calcHist which needs the mask
        # Clear the mask -> set it to black
        self.histogram_mask[0:frame_hsv.shape[1], 0:frame_hsv.shape[0]] = 0

        # Fill the mask with bounding box area
        self.histogram_mask[new_upper_y:new_bottom_y, new_left_x:new_right_x] = 255

        # Create a histogram (256x1 array), where an index correspond with the heu value
        hue_histogram = cv2.calcHist([frame_hsv], HUE, self.histogram_mask, HIST_SIZE, RANGE)

        # TODO: check if there is a faster solution?
        # Find all hue values with the highest frequency
        most_frequent_hue_values = np.where(hue_histogram == np.amax(hue_histogram))[0]

        # Iterate through all configured color ranges
        for mask_color, mask_config in masks_configuration.items():

            # Check if found hue values
            # are in any of configured color ranges
            for entry in mask_config:

                # TODO: currently if the first most_frequent_hue_value is accepted will be returned as a detected color
                for idx in range(len(most_frequent_hue_values)):
                    if entry[0][0] <= most_frequent_hue_values[idx] <= entry[1][0]:
                        detected_color = mask_color

                        # Return an accepted
                        # detected color name
                        return detected_color

        # Return if no configured color detected
        return LegoColor.UNKNOWN_COLOR

    # Estimate possible lego brick dimensions using distance to the board
    # Estimated for resolution 1280/720
    def estimate_possible_lego_dimensions(self, board_distance):

        # Board distance -> square lego side length
        # 1700 - 1799 -> 7-8
        # 1600 - 1699 -> 8-9
        # 1500 - 1599 -> 9-10 ...

        # Take two first digits of the board distance
        board_distance_estimation = int(board_distance / 100)

        # FIXME: error handling
        # Get min length for a square lego brick from the configurations
        try:
            self.min_square_length = int(self.config.get("MIN_ROTATED_SQUARE_LENGTH", str(board_distance_estimation)))
        except:
            logger.error("Not able to calculate a possible lego size, check board distance and configurations")

        if self.min_square_length is not None:

            # Add buffer
            self.min_square_length -= BRICK_LENGTH_BUFFER
            # Add buffer
            self.max_square_length = self.min_square_length + 2 * BRICK_LENGTH_BUFFER

            self.min_square_area = self.min_square_length * self.min_square_length
            self.max_square_area = self.max_square_length * self.max_square_length

            self.min_rectangle_length = 2 * self.min_square_length
            self.max_rectangle_length = 2 * self.max_square_length
            self.min_rectangle_area = self.min_square_length * self.min_rectangle_length
            self.max_rectangle_area = self.max_square_length * self.max_rectangle_length
