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
from LegoOutputStream import LegoOutputStream, LegoOutputChannel


# enable logger
logger = logging.getLogger(__name__)

# TODO: make all this configurable via config
# Side of lego piece rotated bounding box  # TODO: automate
MIN_ROTATED_LENGTH = 10
MAX_ROTATED_LENGTH = 35
MIN_AREA = 70
# Aspect ratio for square and rectangle
MIN_SQ = 0.7
MAX_SQ = 1.35
MIN_REC = 0.2
MAX_REC = 2.5

# FIXME: make it configurable ?
KERNEL_SIZE = (5, 5)

# TODO: make masks configurable ?
masks_configuration = {
    # TODO: adjust yellow so skin will be excluded
    #LegoColor.YELLOW_BRICK: [
    #    (np.array([10, 100, 100]), np.array([20, 255, 200])),
    #],
    # TODO: adjust green so black will be excluded
    #LegoColor.GREEN_BRICK: [
    #    (np.array([55, 50, 50]), np.array([95, 255, 255])),
    #],
    LegoColor.BLUE_BRICK: [
        (np.array([95, 100, 10]), np.array([170, 255, 255])),
    ],
    LegoColor.RED_BRICK: [
        (np.array([0, 120, 120]), np.array([10, 255, 255])),
        (np.array([170, 50, 120]), np.array([180, 255, 255])),
    ]
}


class ShapeDetector:

    # The centroid tracker instance
    tracker = None

    pipeline = None

    def __init__(self, output_stream):

        self.output_stream = output_stream

    # Check if the contour is a lego brick
    # TODO: remove frame if nothing to draw anymore
    def detect_lego_brick(self, contour, frame, color_masks) -> LegoBrick:

        # Initialize the contour name and approximate the contour
        # with Douglas-Peucker algorithm
        contour_shape: LegoShape = LegoShape.UNKNOWN_SHAPE
        detected_color: LegoColor = LegoColor.UNKNOWN_COLOR
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

                # Check color of the lego brick
                for color, mask in color_masks.items():
                    if mask[centroid_y, centroid_x] == 255:
                        detected_color = color
                        break

                # Eliminate wrong colors contours
                if detected_color == LegoColor.UNKNOWN_COLOR:
                    logger.debug("Don't draw -> wrong color")

                # Eliminate very small contours
                elif cv2.contourArea(contour) < MIN_AREA:
                    logger.debug("Don't draw -> area too small")

                else:

                    # Compute the rotated bounding box
                    rect = cv2.minAreaRect(contour)
                    rotated_bbox = np.int0(cv2.boxPoints(rect))

                    contour_shape = self.check_if_square(rotated_bbox)

                    logger.debug("Draw contour:\n Shape: {}\n Color: {}\n "
                                 "Center coordinates: {}, {}\n Contour area: {}".
                                 format(contour_shape, detected_color,
                                        centroid_x, centroid_y, cv2.contourArea(contour)))

                    # return a LegoBrick with the detected parameters
                    return LegoBrick(centroid_x, centroid_y, contour_shape, detected_color)

        return None  # FIXME: CG: we might to differ?

    # Check if the contour has a lego brick shape: square or rectangle
    def check_if_square(self, rotated_bbox) -> LegoShape:

        # Compute the aspect ratio of the two lengths
        # Is set to 0, if the size of lego was not correct
        aspect_ratio = self.calculate_sides_ratio(rotated_bbox)

        if aspect_ratio == 0:
            return LegoShape.UNKNOWN_SHAPE

        # Check if aspect ratio is near 1:1
        if MIN_SQ <= aspect_ratio <= MAX_SQ:
            logger.debug("Square ratio: {}".format(aspect_ratio))
            return LegoShape.SQUARE_BRICK

        # Check if aspect ratio is near 2:1
        elif MIN_REC < aspect_ratio < MAX_REC:
            logger.debug("Rectangle ratio: {}".format(aspect_ratio))
            return LegoShape.RECTANGLE_BRICK

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

    def detect_contours(self, frame):

        # Set red and blue mask
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Do some morphological corrections (fill 'holes' in masks)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, KERNEL_SIZE)

        mask_colors = None
        color_masks = {}
        for mask_color, mask_config in masks_configuration.items():
            masks = None
            for entry in mask_config:
                mask = cv2.inRange(frame_hsv, entry[0], entry[1])
                if masks is None:
                    masks = mask
                else:
                    masks = masks + mask
            dilate = cv2.dilate(masks, kernel, iterations=1)
            if mask_colors is None:
                mask_colors = dilate
            else:
                mask_colors = mask_colors + dilate
            color_masks[mask_color] = mask_colors

        self.output_stream.write_to_channel(LegoOutputChannel.CHANNEL_MASKS, mask_colors)

        # Find contours in the thresholded image
        # Retrieve all of the contours without establishing any hierarchical relationships (RETR_LIST)
        major = cv2.__version__.split('.')[0]
        if major == '3':
            _, contours, hierarchy = cv2.findContours(mask_colors.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        else:
            contours, hierarchy = cv2.findContours(mask_colors.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        return contours, color_masks
