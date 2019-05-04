import cv2
import numpy as np
import math
from shapely import geometry
import logging.config


# configure logging
logger = logging.getLogger(__name__)


class BoardDetector:

    # Array with all polygons of QR-Codes for board corners
    all_codes_polygons_points = [None, None, None, None]

    # ID of the map (metadata read from the code)
    map_id = None

    def __init__(self):
        pass

    # Return pythagoras value
    @staticmethod
    def pythagoras(value_x, value_y):
        value = math.sqrt(value_x ** 2 + value_y ** 2)
        return value

    # Return distance between two points
    def calculate_distance(self, value1_x, value1_y, value2_x, value2_y):
        value_x = value1_x - value2_x
        value_y = value1_y - value2_y
        value = self.pythagoras(value_x, value_y)
        return value

    # Compute position of diagonal board corners, based on position of qr-codes centroids
    def set_corners(self, centroid1, centroid2, centroid_corner_distance):

        corner1 = [0, 0]
        corner2 = [0, 0]

        # Compute vector of length 1 for diagonal direction
        diagonal_distance = self.calculate_distance(centroid1[0], centroid1[1], centroid2[0], centroid2[1])
        diagonal_vector_x_normal = (centroid1[0] - centroid2[0]) / diagonal_distance
        diagonal_vector_y_normal = (centroid1[1] - centroid2[1]) / diagonal_distance

        # Compute vectors of length = centroid_corner_distance for diagonal direction
        diagonal_vector_x = diagonal_vector_x_normal * centroid_corner_distance
        diagonal_vector_y = diagonal_vector_y_normal * centroid_corner_distance

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

    # Read metadata save at the end of the QR-Code data -> map_id
    @staticmethod
    def read_metadata_id(code_data):

        # Split code data of the form: 'C_BL_1'
        map_id = code_data.split('_')[2]
        return map_id

    # Save four polygons of QR-Codes decoded over couple of frames and read metadata
    def read_codes(self, decoded_codes):

        # Check all found codes
        for code in decoded_codes:

            # Decode binary data which is saved in QR-code
            code_data = code.data.decode()

            # If map_id is not known yet
            if self.map_id is None:
                self.map_id = self.read_metadata_id(code_data)

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
    def detect_board(self):

        top_left_corner = None
        top_right_corner = None
        bottom_right_corner = None
        bottom_left_corner = None
        centroids = []
        board_corners = []
        all_board_corners_found = False
        all_codes_flag = True

        # Check if all codes polygons points are available
        for code_polygon in self.all_codes_polygons_points:
            if code_polygon is None:
                logger.debug("Not all codes polygons for board corners are available")
                all_codes_flag = False

        # Continue if all needed data is available
        if all_codes_flag:
            # Iterate through the array with four sets of points for polygons
            for points_idx in range(len(self.all_codes_polygons_points)):
                # Compute the centroid (middle) of the single code
                code_polygon = geometry.Polygon([[point.x, point.y]
                                                 for point in self.all_codes_polygons_points[points_idx]])
                code_centroid = int(code_polygon.centroid.x), int(code_polygon.centroid.y)
                logger.debug("QR-code centroid found: {}".format(code_centroid))

                # Compute the distance between the centroid and the first of corners
                centroid_corner_distance = self.calculate_distance(self.all_codes_polygons_points[points_idx][0].x,
                                                                   self.all_codes_polygons_points[points_idx][0].y,
                                                                   code_polygon.centroid.x, code_polygon.centroid.y)

                # Save all centroids in an array -> [top left, top right, bottom right, bottom left]
                centroids.append(code_centroid)

            # Compute corners position
            # Compute position of the top right and bottom left board corners
            top_left_corner, bottom_right_corner = self.set_corners(
                centroids[0], centroids[2], int(centroid_corner_distance))
            logger.debug("TL corner: {}, BR corner: {}".format(top_left_corner, bottom_right_corner))

            # Compute position of the top left and bottom right board corners
            top_right_corner, bottom_left_corner = self.set_corners(
                centroids[1], centroids[3], int(centroid_corner_distance))
            logger.debug("TR corner: {}, BL corner: {}".format(top_right_corner, bottom_left_corner))

        # If all corners are found, save them in the right order
        if top_left_corner is not None and top_right_corner is not None and \
                bottom_right_corner is not None and bottom_left_corner is not None:
            board_corners = [top_left_corner, top_right_corner, bottom_right_corner, bottom_left_corner]
            logger.debug("board_corners: {}".format(board_corners))
            all_board_corners_found = True

            return all_board_corners_found, board_corners

        return all_board_corners_found, board_corners

    # Find min and max for x and y position of the board
    @staticmethod
    def find_min_max(corners):
        x = []
        y = []
        for corner in corners:
            x.append(corner[0])
            y.append(corner[1])
        return min(x), min(y), max(x), max(y)

    # Wrap the frame perspective to a top-down view (rectangle)
    def rectify(self, image, corners):

        # Save given corners in a numpy array
        source_corners = np.zeros((4, 2), dtype="float32")
        source_corners[0] = corners[0]
        source_corners[1] = corners[1]
        source_corners[2] = corners[2]
        source_corners[3] = corners[3]

        # Compute width and height of the board
        min_x, min_y, max_x, max_y = self.find_min_max(corners)
        board_size_width = max_x - min_x
        board_size_height = max_y - min_y

        # Construct destination points which will be used to map the board to a top-down view
        destination_corners = np.array([
            [0, 0],
            [board_size_width - 1, 0],
            [board_size_width - 1, board_size_height - 1],
            [0, board_size_height - 1]], dtype="float32")

        # Calculate the perspective transform matrix
        matrix = cv2.getPerspectiveTransform(source_corners, destination_corners)
        rectified_image = cv2.warpPerspective(image, matrix, (board_size_width, board_size_height))

        return rectified_image, board_size_height, board_size_width
