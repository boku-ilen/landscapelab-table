# TODO: optimization possibilities:
# detect inner corners of markers to exclude the QR-Code-markers from analysis
# temporal filtering (IIR filter) to remove "holes" (depth=0), hole-filling
# edge-preserving filtering to smooth the depth noise
# changing the depth step-size
# IR pattern removal

import logging
from builtins import staticmethod
from typing import Optional, Tuple

import cv2
import numpy as np
import math

from numpy import ndarray

from LabTable.Model.Brick import Brick, BrickShape, BrickColor, Token

# enable logger
logger = logging.getLogger(__name__)

# Aspect ratio for square and rectangle
MIN_SQ = 0.7
MAX_SQ = 1.35
MIN_REC = 0.2
MAX_REC = 2.5
BRICK_LENGTH_BUFFER = 2

# Camera's depth field of view
HORIZONTAL_ANGLE = 65
VERTICAL_ANGLE = 40
# brick real size in cm
BRICK_SHORT_SIDE = 1.58
BRICK_LONG_SIDE = 3.18

# Hue histogram configurations
# Color channels
HUE = 0
SATURATION = 1
VALUE = 2
# Histogram size
HIST_SIZE = 181

# TODO: make masks configurable ?
# OpenCV supports:
# H-value range (0 to 180)
# S-value range (0 to 255)
# V-value range (0 to 255)

# TODO: set in masks_configuration only hue and saturation/value separately, the same for all colors?
MIN_SATURATION = 100
MAX_SATURATION = 255


class ShapeDetector:

    # Initialize possible brick sizes
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
        self.resolution_width = config.get("video_resolution", "width")
        self.masks_configuration = config.get("brick_colors")

    # Check if the contour is a brick
    def detect_brick(self, contour, frame) -> Optional[Brick]:

        # Initialize the contour name and approximate the contour
        # with Douglas-Peucker algorithm
        epsilon = 0.1 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the contour has 4 vertices
        if len(approx) == 4:

            # Compute the centroid of the contour
            moments_dict = cv2.moments(contour)
            if moments_dict["m00"] != 0:
                centroid_x = int((moments_dict["m10"] / moments_dict["m00"]))
                centroid_y = int((moments_dict["m01"] / moments_dict["m00"]))

                # Eliminate too small contours
                area = cv2.contourArea(contour)
                if self.min_square_area <= area <= self.max_rectangle_area:

                    # Check if contour is a rectangle or square
                    contour_shape, aspect_ratio, rotated_bbox_lengths = self.classify_shape(approx)
                    if contour_shape is not BrickShape.UNKNOWN_SHAPE:

                        # Compute the bounding box of the contour
                        bbox = cv2.boundingRect(approx)

                        # Find the most frequent color (heu value)
                        # in the bounding box
                        detected_color, avg_hue = self.classify_color(bbox, frame)

                        # Eliminate wrong colors contours
                        if detected_color is not BrickColor.UNKNOWN_COLOR:

                            # return a Brick with the detected parameters
                            token = Token(contour_shape, BrickColor[detected_color])
                            brick = Brick(centroid_x, centroid_y, token)
                            brick.aspect_ratio = aspect_ratio
                            brick.average_detected_color = detected_color
                            brick.detected_area = area
                            brick.rotated_bbox_lengths = rotated_bbox_lengths
                            brick.average_detected_color = avg_hue

                            # log debug information
                            logger.debug("created brick {} with area {} and hue {}".format(brick, area, avg_hue))

                            return brick
        return None

    # Check if the contour has a brick shape: square or rectangle
    def classify_shape(self, rotated_bbox) -> Tuple[BrickShape, float, ndarray]:

        brick_shape = BrickShape.UNKNOWN_SHAPE
        aspect_ratio = 0
        rotated_bbox_lengths = self.calculate_rotated_bbox_lengths(rotated_bbox)
        logger.debug("Rotated bbox size: {}".format(rotated_bbox_lengths))

        # Prevent division by zero
        if int(rotated_bbox_lengths[1]) is not 0:

            # Compute the aspect ratio of the two lengths
            aspect_ratio = int(rotated_bbox_lengths[0]) / int(rotated_bbox_lengths[1])
            logger.debug("detected aspect ratio is {}".format(aspect_ratio))

            # Check if aspect ratio is near 1:1
            if MIN_SQ <= aspect_ratio <= MAX_SQ:

                # Check if sides of the square brick are not too short/long
                if not (self.min_square_length < rotated_bbox_lengths[0] < self.max_square_length) \
                        and (self.min_square_length < rotated_bbox_lengths[1] < self.max_square_length):
                    logger.debug("wrong square sides lengths")

                else:
                    logger.debug("detected SQUARE brick contour")
                    brick_shape = BrickShape.SQUARE_BRICK

            # Check if aspect ratio is near 2:1
            elif MIN_REC < aspect_ratio < MAX_REC:

                # Check if sides of the rectangle brick are not too short/long
                if not (self.min_rectangle_length < rotated_bbox_lengths[0] < self.max_rectangle_length) \
                        and (self.min_rectangle_length < rotated_bbox_lengths[1] < self.max_rectangle_length):
                    logger.debug("wrong rectangle sides lengths")

                else:
                    logger.debug("detected RECTANGLE brick contour")
                    brick_shape = BrickShape.RECTANGLE_BRICK

            # finally reject shape
            else:
                logger.debug("could not classify shape because of aspect ratio")

        return brick_shape, aspect_ratio, rotated_bbox_lengths

    # Compute two sides lengths of the contour, which have a common corner
    @staticmethod
    def calculate_rotated_bbox_lengths(rotated_bbox) -> ndarray:

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

    # this is used to classify
    def classify_color(self, bbox, frame):

        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Save dimensions of the bounding box
        (left_x, upper_y, width, height) = bbox

        # Calculate a new bounding box which is 25% of the old one and is placed in its middle
        new_width = int(width / 2)
        new_height = int(height / 2)
        new_left_x = left_x + int(new_width / 2)
        new_upper_y = upper_y + int(new_height / 2)

        # Create a histogram with hue values of pixels which already have a correct saturation
        hue_histogram = np.zeros(HIST_SIZE)
        max_frequency = 0
        most_frequent_hue_value = None
        for x in range(new_width):
            for y in range(new_height):

                # Take only the area of the brick bounding box
                hsv_bbox = frame_hsv[new_upper_y + y, new_left_x + x]

                # Check if saturation is correct
                if MIN_SATURATION <= hsv_bbox[SATURATION] <= MAX_SATURATION:

                    # Add hue value to the histogram
                    hue_histogram[hsv_bbox[HUE]] += 1

                    # Save the most frequent hue value
                    if hue_histogram[hsv_bbox[HUE]] > max_frequency:
                        max_frequency = hue_histogram[hsv_bbox[HUE]]
                        most_frequent_hue_value = hsv_bbox[HUE]

        if most_frequent_hue_value is not None:
            # Iterate through all configured color ranges
            for mask_color, mask_config in self.masks_configuration.items():

                # Check if found hue values are in any of configured color ranges
                for entry in mask_config:

                    # TODO: currently only one of the most frequent hue values will be returned as a detected color
                    if entry[0][HUE] <= most_frequent_hue_value <= entry[1][HUE]:
                        detected_color = mask_color

                        # Return an accepted detected color name
                        return detected_color, most_frequent_hue_value

        # Return if no configured color detected
        return BrickColor.UNKNOWN_COLOR, most_frequent_hue_value

    @staticmethod
    def calculate_tangent(angle):

        tangent = math.tan(angle * math.pi / 180)
        return tangent

    # Calculate possible brick dimensions using distance to the board
    def calculate_possible_brick_dimensions(self, board_distance):

        # Use a tangent of the half of horizontal angle to calculate the display width in mm
        horizontal_side_length = 2 * board_distance * self.calculate_tangent(HORIZONTAL_ANGLE / 2)
        # Calculate how many pixels give one centimeter
        one_cm_in_pixel = 10 * self.resolution_width / horizontal_side_length

        # Calculate the squared brick side
        square_length = one_cm_in_pixel * BRICK_SHORT_SIDE
        # Add buffer
        self.min_square_length = square_length - BRICK_LENGTH_BUFFER
        self.max_square_length = square_length + BRICK_LENGTH_BUFFER
        # Calculate the squared brick area
        self.min_square_area = self.min_square_length * self.min_square_length
        self.max_square_area = self.max_square_length * self.max_square_length

        # Calculate the long side of a rectangle brick
        rectangle_length = one_cm_in_pixel * BRICK_LONG_SIDE
        # Add buffer
        self.min_rectangle_length = rectangle_length - BRICK_LENGTH_BUFFER
        self.max_rectangle_length = rectangle_length + BRICK_LENGTH_BUFFER
        # Calculate the squared brick area
        self.min_rectangle_area = self.min_square_length * self.min_rectangle_length
        self.max_rectangle_area = self.max_square_length * self.max_rectangle_length
