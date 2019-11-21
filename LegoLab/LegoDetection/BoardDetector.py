import pyzbar.pyzbar as pyzbar
import cv2
import numpy as np
import math
from shapely import geometry
import logging.config

from ..ExtentTracker import ExtentTracker
from ..Extent import Extent
from ..Board import Board


# configure logging
logger = logging.getLogger('MainLogger')

# Objects in greater distance to the board than (1 +- CLIP) * x will be excluded from processing
CLIP = 0.1

# Number of frames for
# computing background average
MAX_LOOP_NUMBER = 30

# accumulate weighted parameter
INPUT_WEIGHT = 0.5

# Maximum value to use
# with the THRESH_BINARY
MAX_VALUE = 255

# Number of frames for
# changing threshold_qrcode
# when detecting the board corners
MAX_FRAMES_NUMBER = 20

# Adjusting threshold_qrcode step
THRESHOLD_STEP = 16
MAX_THRESHOLD = 255


# this class manages the extent to detect and reference the extent of
# the board related to the video stream
class BoardDetector:

    background = None

    def __init__(self, config, threshold_qrcode):

        self.config = config

        # Initialize the board
        self.board = Board()

        # Threshold for finding QR-Codes
        # To change the threshold use an optional parameter
        self.board.threshold_qrcode = threshold_qrcode

        # Array with all polygons of QR-Codes for board corners
        self.all_codes_polygons_points = [None, None, None, None]
        self.found_codes_number = 0
        self.code_found_flag = False

        # Get the resolution from config file
        self.frame_width = self.config.get("resolution", "width")
        self.frame_height = self.config.get("resolution", "height")

        self.current_loop = 0

        self.detect_corners_frames_number = 0

    # Compute pythagoras value
    @staticmethod
    def pythagoras(value_x, value_y):

        value = math.sqrt(value_x ** 2 + value_y ** 2)

        # Return pythagoras value
        return value

    # Compute distance between two points
    @staticmethod
    def calculate_distance(value1_x, value1_y, value2_x, value2_y):

        value_x = value1_x - value2_x
        value_y = value1_y - value2_y
        distance = BoardDetector.pythagoras(value_x, value_y)

        # Return distance between two points
        return distance

    # Compute normal vector
    @staticmethod
    def normal_vector(point1, point2):
        distance = BoardDetector.calculate_distance(point1[0], point1[1], point2[0], point2[1])
        normal_vector_x = (point1[0] - point2[0]) / distance
        normal_vector_y = (point1[1] - point2[1]) / distance

        # Return normal vector
        return normal_vector_x, normal_vector_y

    # Compute position of diagonal board corners, based on position of qr-codes centroids
    def set_corners(self, qrcode_points, centroid1, centroid2, centroid_corner_distance):

        corner1 = [0, 0]
        corner2 = [0, 0]

        # TODO: write a function
        # Compute vector of length 1 for diagonal of board corners (between two centroids)
        board_diagonal_normal_vector = self.normal_vector(centroid1, centroid2)

        # Compute vector of length 1 for both diagonals of a qr_code square and choose the right one
        # Compute vector of length 1 for the first diagonal
        qrcode_diagonal1_normal_vector = self.normal_vector(qrcode_points[0], qrcode_points[2])

        # Compute vector of length 1 for the second diagonal
        qrcode_diagonal2_normal_vector = self.normal_vector(qrcode_points[1], qrcode_points[3])

        # Choose the right diagonal, must have the same sign as the diagonal of given board corners
        # Minus * Minus -> Plus
        # Plus * Plus -> Plus
        # Plus * Minus -> Minus
        # If the product is > 0, it is the right diagonal of the qrcode
        if board_diagonal_normal_vector[0] * qrcode_diagonal1_normal_vector[0] * \
                board_diagonal_normal_vector[1] * qrcode_diagonal1_normal_vector[1] > 0:
            diagonal = qrcode_diagonal1_normal_vector
        else:
            diagonal = qrcode_diagonal2_normal_vector

        # Compute vectors of length = centroid_corner_distance for diagonal direction
        diagonal_vector_x = diagonal[0] * centroid_corner_distance
        diagonal_vector_y = diagonal[1] * centroid_corner_distance

        # Ensure that vectors are positive in x and y directions
        diagonal_vector_x = self.pythagoras(diagonal_vector_x, 0)
        diagonal_vector_y = self.pythagoras(diagonal_vector_y, 0)

        # Compute position of corners (distance between corners must be bigger than between centroids)
        if centroid1[0] < centroid2[0]:
            corner1[0] = centroid1[0] - diagonal_vector_x
            corner2[0] = centroid2[0] + diagonal_vector_x
        else:
            corner1[0] = centroid1[0] + diagonal_vector_x
            corner2[0] = centroid2[0] - diagonal_vector_x

        if centroid1[1] < centroid2[1]:
            corner1[1] = centroid1[1] - diagonal_vector_y
            corner2[1] = centroid2[1] + diagonal_vector_y
        else:
            corner1[1] = centroid1[1] + diagonal_vector_y
            corner2[1] = centroid2[1] - diagonal_vector_y

        # Cast to int
        corner1[0] = int(corner1[0])
        corner1[1] = int(corner1[1])
        corner2[0] = int(corner2[0])
        corner2[1] = int(corner2[1])

        # Do not allow for position lower than 0
        if corner1[0] < 0:
            corner1[0] = 0
        if corner1[1] < 0:
            corner1[1] = 0
        if corner2[0] < 0:
            corner2[0] = 0
        if corner2[1] < 0:
            corner2[1] = 0

        return corner1, corner2

    # Save four polygons of QR-Codes decoded over couple of frames and read metadata
    def read_qr_codes(self, decoded_codes):

        # Check all found codes
        for code in decoded_codes:

            # Decode binary data which is saved in QR-code
            code_data = code.data.decode()

            # If data in array with top left, top right, bottom right, bottom left
            # data is not set yet, add the new found data
            if "TL" in code_data and self.all_codes_polygons_points[0] is None:
                self.all_codes_polygons_points[0] = code.polygon
            if "TR" in code_data and self.all_codes_polygons_points[1] is None:
                self.all_codes_polygons_points[1] = code.polygon
            if "BR" in code_data and self.all_codes_polygons_points[2] is None:
                self.all_codes_polygons_points[2] = code.polygon
            if "BL" in code_data and self.all_codes_polygons_points[3] is None:
                self.all_codes_polygons_points[3] = code.polygon

        logger.debug("All found codes polygon points: {}".format(self.all_codes_polygons_points))

    # Detect the board using four QR-Codes in the board corners
    def detect_board(self, color_image):

        # Compute difference between background and the current frame
        diff = self.subtract_background(color_image)

        # Invert image
        looking_for_qr_code_image = 255 - diff

        # Decode QR or Bar-Codes from both
        # black-white and color image
        decoded_codes = pyzbar.decode(looking_for_qr_code_image)
        if not decoded_codes:
            decoded_codes = pyzbar.decode(color_image)

        # Mark found QR-codes on the color image
        self.display_found_codes(color_image, decoded_codes)

        # Read codes which were decoded in this frame:
        # save polygons in the array self.board_detector.all_codes_polygons_points
        # and read metadata
        self.read_qr_codes(decoded_codes)
        # FIXME: end move

        top_left_corner = None
        top_right_corner = None
        bottom_right_corner = None
        bottom_left_corner = None
        centroids = []
        all_board_corners_found = False
        centroid_corner_distance = None

        # Count found qr-codes
        self.board.found_codes_number = sum(code is not None for code in self.all_codes_polygons_points)

        # Update the flag
        if self.board.found_codes_number > self.found_codes_number:

            self.found_codes_number = self.board.found_codes_number
            if self.code_found_flag is False:
                self.code_found_flag = True
                self.detect_corners_frames_number = 0

            # Continue if all needed data is available
        if self.found_codes_number == 4:
            # Iterate through the array with four sets of points for polygons
            for points_idx in range(len(self.all_codes_polygons_points)):

                # Compute the centroid (middle) of the single code
                code_polygon = geometry.Polygon([[point.x, point.y]
                                                 for point in self.all_codes_polygons_points[points_idx]])
                code_centroid = int(code_polygon.centroid.x), int(code_polygon.centroid.y)
                logger.debug("QR-code centroid found: {}".format(code_centroid))

                # Compute the distance between the centroid and the first of corners
                centroid_corner_distance = BoardDetector.calculate_distance\
                    (self.all_codes_polygons_points[points_idx][0].x,
                     self.all_codes_polygons_points[points_idx][0].y,
                     code_polygon.centroid.x, code_polygon.centroid.y)

                # Save all centroids in an array -> [top left, top right, bottom right, bottom left]
                centroids.append(code_centroid)

            # Compute corners position
            if centroid_corner_distance is not None:

                # Compute position of the top right and bottom left board corners
                top_left_corner, bottom_right_corner = \
                    self.set_corners(self.all_codes_polygons_points[0],
                                     centroids[0], centroids[2], int(centroid_corner_distance))

                logger.debug("TL corner: {}, BR corner: {}".format(top_left_corner, bottom_right_corner))

                # Compute position of the top left and bottom right board corners
                top_right_corner, bottom_left_corner = \
                    self.set_corners(self.all_codes_polygons_points[1],
                                     centroids[1], centroids[3], int(centroid_corner_distance))

                logger.debug("TR corner: {}, BL corner: {}".format(top_right_corner, bottom_left_corner))

        # If all corners are found, save them in the right order
        if top_left_corner is not None and top_right_corner is not None and \
                bottom_right_corner is not None and bottom_left_corner is not None:

            self.board.corners = [top_left_corner, top_right_corner, bottom_right_corner, bottom_left_corner]
            logger.debug("board_corners: {}".format(self.board.corners))
            all_board_corners_found = True

        return all_board_corners_found

    # Find min and max for x and y position of the board
    @staticmethod
    def find_min_max(corners):
        x = []
        y = []
        # FIXME: x & y are sometimes switched?!
        for corner in corners:
            x.append(corner[0])
            y.append(corner[1])
            # x.append(corner[1])
            # y.append(corner[0])
        return min(x), min(y), max(x), max(y)

    # Wrap the frame perspective to a top-down view (rectangle)
    def rectify(self, image, corners):

        # Save given corners in a numpy array
        source_corners = np.zeros((4, 2), dtype="float32")
        source_corners[0] = corners[0]
        source_corners[1] = corners[1]
        source_corners[2] = corners[2]
        source_corners[3] = corners[3]

        # If not done yet, compute width and height of the board
        if self.board.width == 1:

            # Compute width and height of the board
            self.compute_board_size(corners)

        # Construct destination points which will be used to map the board to a top-down view
        destination_corners = np.array([
            [0, 0],
            [self.board.width - 1, 0],
            [self.board.width - 1, self.board.height - 1],
            [0, self.board.height - 1]], dtype="float32")

        # Calculate the perspective transform matrix
        matrix = cv2.getPerspectiveTransform(source_corners, destination_corners)
        rectified_image = cv2.warpPerspective(image, matrix, (self.board.width, self.board.height))

        return rectified_image

    # Compute board size and set in configs
    def compute_board_size(self, corners):

        min_x, min_y, max_x, max_y = self.find_min_max(corners)

        # Compute board size
        self.board.width = max_x - min_x
        self.board.height = max_y - min_y

        ExtentTracker.get_instance().board = Extent.from_rectangle(0, 0, self.board.width, self.board.height)
        logger.info('board has been set')

    # Display QR-codes location
    @staticmethod
    def display_found_codes(frame, decoded_objects):

        # Loop over all decoded objects
        for decoded_object in decoded_objects:
            points = decoded_object.polygon

            # If the points do not form a quad, find convex hull
            if len(points) > 4:
                hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                hull = list(map(tuple, np.squeeze(hull)))
            else:
                hull = points

            # Number of points in the convex hull
            n = len(hull)

            # Draw the convex hull
            for j in range(0, n):
                cv2.line(frame, hull[j], hull[(j + 1) % n], (255, 0, 0), 3)

    # FIXME: fix the method and use it
    # Analyze only objects on the board distance
    def clip_board(self, color_image, depth_image_3d):

        # clipping the color image to the area with the right distance values
        # TODO: find a working pythonic way
        if self.board.distance:
            clipped_color_image = np.where(
                (depth_image_3d > self.board.distance * (1 + CLIP)) |
                (depth_image_3d < self.board.distance * (1 - CLIP)),
            0, color_image)
        else:
            clipped_color_image = color_image
        # not working properly  # FIXME: why is this then still here?
        # clipped_color_image = np.where((depth_image_3d > clip_dist * (1 + CLIP)).all()
        #                               or (depth_image_3d < clip_dist * (1 - CLIP)).all(),
        #                               0, color_image)

        return clipped_color_image

    # Compute region of interest (board area) from the color image
    def rectify_image(self, region_of_interest, color_image):

        # Check if found QR-code markers positions are included in the frame size
        if all([0, 0] < corners < [color_image.shape[1], color_image.shape[0]]
               for corners in self.board.corners):

            # Eliminate perspective transformations and show only the board
            rectified_image = self.rectify(color_image, self.board.corners)
            # TODO: use clipped color image
            # rectified_image =  self.board_detector.rectify(clipped_color_image, board_corners)

            # Set ROI to black and add only the rectified board, where objects are searched
            region_of_interest[0:self.frame_height, 0:self.frame_width] = [0, 0, 0]
            region_of_interest[0:self.board.height, 0:self.board.width] = rectified_image

        return region_of_interest

    # Returns difference between
    # background and current frame
    def subtract_background(self, color_image):

        # Subtract background
        diff = cv2.absdiff(color_image, self.background.astype("uint8"))
        diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        ret_val, diff = cv2.threshold(diff, self.board.threshold_qrcode, MAX_VALUE, cv2.THRESH_BINARY)
        logger.debug("Using threshold for qr-codes {}".format(self.board.threshold_qrcode))

        # Return difference between
        # the current frame and background
        return diff

    # saves the average image over a certain time period returns true if enough iterations were done
    def compute_background(self, color_image):

        # Save background
        if self.current_loop == 0:
            self.background = color_image.copy().astype("float")

        if self.current_loop < MAX_LOOP_NUMBER:
            # Update a running average
            cv2.accumulateWeighted(color_image, self.background, INPUT_WEIGHT)
            self.current_loop += 1
        else:
            return True

        return False

    # Adjust cyclically the threshold for finding qr-codes
    # Example: 60 -> 76 -> 44 -> 90 -> 18 -> ...
    def adjust_threshold_qrcode(self):

        # Count frames
        self.detect_corners_frames_number += 1

        # Every X frames change the threshold
        if self.detect_corners_frames_number % MAX_FRAMES_NUMBER == 0:

            # Count the number of threshold changes
            loop = int(self.detect_corners_frames_number / MAX_FRAMES_NUMBER)

            # Use the configured step to change the threshold
            if loop * THRESHOLD_STEP < MAX_THRESHOLD:
                step = THRESHOLD_STEP

            # If the whole range checked and no qr-code found
            # Start again with smaller steps
            else:
                step = int(THRESHOLD_STEP / 2)
                self.detect_corners_frames_number = 0

            # If at lest one qr-code found do smaller steps
            if self.code_found_flag:
                step = int(step / 4)

            else:
                step = step

            # For odd loops changed the sign
            if loop % 2 == 0:
                loop *= -1

            # Adjust the threshold
            self.board.threshold_qrcode += loop * step

            # Allow only threshold 0-255
            if self.board.threshold_qrcode < 0:
                self.board.threshold_qrcode += MAX_THRESHOLD
            elif self.board.threshold_qrcode > MAX_THRESHOLD:
                self.board.threshold_qrcode -= MAX_THRESHOLD


