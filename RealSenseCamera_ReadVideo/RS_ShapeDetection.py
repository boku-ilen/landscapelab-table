
# TODO: optimization possibilities:
# detect inner corners of markers to exclude the QR-Code-markers from analysis
# temporal filtering (IIR filter) to remove "holes" (depth=0), hole-filling
# edge-preserving filtering to smooth the depth noise
# changing the depth step-size
# IR pattern removal

# Used pyrealsense2 on License: Apache 2.0.
from builtins import staticmethod

# Used libraries versions:
# python=3.6.8
# opencv=3.3.1 (opencv=4.1 released, to update when working with python 3.7)
# pyrelasense=2.20.0.714, not working with python 3.7 yet (https://pypi.org/project/pyrealsense2/)
# pyzbar=0.1.8

import pyrealsense2 as rs  # TODO: ship a binary build
import numpy as np
import cv2  # TODO: fix the requirements.txt or provide library
import colorsys
import logging.config
import time
import requests
import math
from shapely import geometry
import pyzbar.pyzbar as pyzbar
from QRCodeDetection.QRCodeDetection import QRCodeDetector
from Tracking.Tracker import Tracker
#from Tracking.MyTracker import MyTracker


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
VIDEO_FILE = 'outpy.avi'
# Side of lego piece  # TODO: automate
MIN_LENGTH = 4
MAX_LENGTH = 35
MIN_AREA = 70
# Objects in greater distance to the board than (1 +- CLIP) * x will be excluded from processing
CLIP = 0.1
# Aspect ratio for square and rectangle
MIN_SQ = 0.7
MAX_SQ = 1.35
MIN_REC = 0.2
MAX_REC = 2.5
# Accepted HSV colors
BLUE_MIN = (0.53, 0.33, 105)
BLUE_MAX = (0.65, 1, 255)
RED_MIN = (0.92, 0.40, 140)
RED_MAX = (1, 1, 255)


class ShapeDetector:

    # Flag for location from request
    location_json = None

    # The centroid tracker instance
    centroid_tracker = None

    pipeline = None

    # The configuration instance of the realsense camera
    realsense_config = None

    depth_scale = None

    def __init__(self):

        # Configure depth and color streams
        self.pipeline = rs.pipeline()
        self.realsense_config = rs.config()
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
        self.qrcode_detector = QRCodeDetector()

        # Initialize the centroid tracker
        self.centroid_tracker = Tracker()
        # centroid_tracker = MyTracker()

        # TODO: read metadata (= 1) from QR-code
        # Geolocation request
        self.location_json = requests.get("http://127.0.0.1:8000/location/map/1.json")
        print(self.location_json)

    # Check if the contour is a lego brick
    def detect_lego_brick(self, contour, frame):

        # Initialize the contour name and approximate the contour
        # with Douglas-Peucker algorithm
        contour_name = "shape"
        epsilon = 0.1 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the contour has 4 vertices
        if len(approx) == 4:

            # Compute the rotated bounding box
            rect = cv2.minAreaRect(contour)
            rotated_bbox = np.int0(cv2.boxPoints(rect))

            # Draw red contours for all found contours (for testing purposes)
            cv2.drawContours(frame, [rotated_bbox], 0, (0, 0, 255), 2)

            # Compute the bounding box of the contour and the aspect ratio
            (x, y, w, h) = cv2.boundingRect(approx)
            bbox = (x, y, w, h)

            # Draw a blue bounding box (for testing purposes)
            # cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # Check the size and color of the contour to decide if it is a lego brick
            if (MIN_LENGTH < h < MAX_LENGTH) & (MIN_LENGTH < w < MAX_LENGTH):
                contour_name = self.check_if_square(rotated_bbox)

            # return contour name and its bounding box
            return contour_name, bbox

        # return contour name == "shape" and empty bounding box
        return contour_name, []

    # Check if the contour has a lego brick shape: square or rectangle
    def check_if_square(self, rotated_bbox):

        # Compute two sides lengths of the contour, which have a common corner
        length_a, length_b = self.calculate_size(rotated_bbox)

        # Compute the aspect ratio of the two lengths
        aspect_ratio = int(length_a) / int(length_b)
        contour_name = "shape"

        # Check if aspect ratio is near 1:1
        if MIN_SQ <= aspect_ratio <= MAX_SQ:
            contour_name = "square"
            logger.debug("Square size: {}, {}".format(length_a, length_b))

        # Check if aspect ratio is near 2:1
        elif MIN_REC < aspect_ratio < MAX_REC:
            contour_name = "rectangle"
            logger.debug("Rectangle size: {}, {}".format(length_a, length_b))

        # return contour name
        return contour_name

    # Compute two sides lengths of the contour, which have a common corner
    @staticmethod
    def calculate_size(rotated_bbox):

        # Initialize a list for sides lengths of the contour
        sides_lengths_list = []

        # Compute three lengths for three corners of rotated bounding box
        # These are a triangle, a half of bounding box
        for corner in range(3):
            sides_lengths_list.append(np.linalg.norm(rotated_bbox[0] - rotated_bbox[corner + 1]))

        # Delete the highest length value, which is a diagonal of bounding box
        # Only two sides lengths, which have a common corner, are remaining in the array
        result = np.delete(sides_lengths_list, np.argmax(sides_lengths_list))

        # Return two sides lengths of the rotated bounding box
        return result

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

    # Detect the board using four QR-Codes in the board corners
    def detect_board(self, decoded_codes):

        # TODO: save found centroid even if not all 4 qr-codes are found in the same frame
        top_left_corner = None
        top_right_corner = None
        bottom_right_corner = None
        bottom_left_corner = None
        top_left_centroid = None
        top_right_centroid = None
        bottom_right_centroid = None
        bottom_left_centroid = None
        board_corners = None

        # Check all found codes
        for code in decoded_codes:

            # Decode binary data which is saved in QR-code
            code_data = code.data.decode()

            # Compute outer corners of the board and read metadata
            # All data with corners information start with "C_"
            if "C_" in code_data:

                # TODO: read metadata
                # The last part of string "_X" is the number of the map

                # Compute the centroid (middle) of the single code
                code_polygon = geometry.Polygon([[point.x, point.y] for point in code.polygon])
                code_centroid = int(code_polygon.centroid.x), int(code_polygon.centroid.y)
                # Compute the distance between the centroid and one of corners
                centroid_corner_distance = self.calculate_distance(code.polygon[0].x, code.polygon[0].y,
                                                                   code_polygon.centroid.x, code_polygon.centroid.y)
                # Set corners properly
                if "TL" in code_data:
                    top_left_centroid = code_centroid
                elif "TR" in code_data:
                    top_right_centroid = code_centroid
                elif "BR" in code_data:
                    bottom_right_centroid = code_centroid
                elif "BL" in code_data:
                    bottom_left_centroid = code_centroid

                # If centroids are known, compute corners position
                # Compute position of the top left and bottom right board corners
                if top_right_centroid is not None and bottom_left_centroid is not None:
                    top_right_corner, bottom_left_corner = self.set_corners(
                        top_right_centroid, bottom_left_centroid, int(centroid_corner_distance))

                # Compute position of the top right and bottom left board corners
                if top_left_centroid is not None and bottom_right_centroid is not None:
                    top_left_corner, bottom_right_corner = self.set_corners(
                        top_left_centroid, bottom_right_centroid, int(centroid_corner_distance))

        # If all corners are found, save them in the right order
        if top_left_corner is not None and top_right_corner is not None and \
                bottom_right_corner is not None and bottom_left_corner is not None:
            board_corners = [top_left_corner, top_right_corner, bottom_right_corner, bottom_left_corner]

        # TODO: rectify with outer_corners = [top left, top right, bottom right, bottom left]

    # TODO: (0, 1 000 000) or float, compute geographic coordinates
    # Return coordinates of the detected object for (min, max) = (0, 1000)
    # (0, 0) is the outer corner of the middle QR-Code marker
    @staticmethod
    def calculate_coordinates(board_size, coordinates, max=1000):
        return int(coordinates[0] * max / board_size), \
               int(coordinates[1] * max / board_size)

    # Run lego bricks detection and tracking code
    def run(self, record_video=False):

        # Define the codec and create VideoWriter object. The output is stored in 'outpy.avi' file.
        # Define the fps to be equal to 10. Also frame size is passed.
        video_handler = None
        if record_video:
            video_handler = cv2.VideoWriter(VIDEO_FILE, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                            10, (int(WIDTH), int(HEIGHT)))

        # Initialize the clipping distance
        clip_dist = 0

        # Initialize board detection and QR-code detector result flags
        board_detected = False
        qr_code_detector_result = False

        # Initialize squared board size and middle of the board
        board_size = HEIGHT
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

                # Get aligned frames
                aligned_depth_frame = aligned_frames.get_depth_frame()  # aligned_depth_frame is a 640x480 depth image
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
                clipped_color_image = np.where((depth_image_3d > clip_dist * (1 + CLIP)).all()
                                               or (depth_image_3d < clip_dist * (1 - CLIP)).all(),
                                               0, color_image)

                # Set ROI as the color_image to set the same size
                region_of_interest = color_image

                # Show color image
                cv2.imshow('Color', color_image)

                # Decode QR or Bar-Codes
                decoded_codes = pyzbar.decode(color_image)

                # Detect the board (new solution) and read metadata
                self.detect_board(decoded_codes)

                # Get the distance to the board (to the middle of the frame)
                if not clip_dist or not board_detected:
                    logger.debug("clip_dist_: {}".format(clip_dist))
                    logger.debug("board detected: {}".format(board_detected))
                    clip_dist = aligned_depth_frame.get_distance(middle_x, middle_y) / self.depth_scale
                    logger.debug("Distance to the table is: {}".format(clip_dist))

                # Detection of the board with QR-Code Detector, detecting until the board is found
                # Detect the corners of the board, save position and eliminate perspective transformations
                # The board must be square, markers should be placed precisely
                # TODO: if camera is lightly moving position must be updated
                if not board_detected:
                    logger.debug("Board detecting")
                    # Compute True/False result and outer corners of QR-code markers
                    qr_code_detector_result, markers = self.qrcode_detector.qr_code_outer_corners(color_image)

                if qr_code_detector_result:

                    # Check if found QR-code markers positions are included in the frame size
                    if all((0, 0) < tuple(marker) < (color_image.shape[1], color_image.shape[0]) for marker in markers):

                        logger.debug("Detecting lego bricks")
                        # Set board detection flag as True
                        board_detected = True

                        # Compute board local coordinates
                        minX, minY, maxX, maxY = self.qrcode_detector.find_minmax(markers)
                        board_size = maxX-minX

                        # Eliminate perspective transformations and change to square
                        rectified = self.qrcode_detector.rectify(clipped_color_image, markers, (board_size, board_size))

                        # Set ROI to black and add only the rectified board, where objects are searched
                        region_of_interest[0:HEIGHT, 0:WIDTH] = [0, 0, 0]
                        region_of_interest[0:board_size, 0:board_size] = rectified

                else:
                    logger.debug("No QR-code detector result")
                    region_of_interest[0:HEIGHT, 0:WIDTH] = [0, 0, 0]

                # Show the board (region of interest)
                cv2.imshow('ROI', region_of_interest)
                frame = region_of_interest

                # TODO: use hierarchy to find contours without changing to black
                # TODO: or try changing to black only light colors using hsv
                # Convert the image to grayscale
                img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Change whiteboard to black (contours are to find from black background)
                thresh = cv2.threshold(img_gray, 140, 255, cv2.THRESH_BINARY)[1]
                frame[thresh == 255] = 0

                # TODO: delete this part if black lego bricks should be found
                # Remove gray/black colors to ignore shadows and QR-code markers
                frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                thresh = cv2.inRange(frame_hsv, (0, 0, 0), (255, 255, 120))
                frame[thresh == 255] = 0

                # Convert the resized image to grayscale, blur it slightly,
                # and threshold it to optimize searching for contours
                img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
                thresh = cv2.threshold(blurred, 55, 255, cv2.THRESH_BINARY)[1]

                # Find contours in the thresholded image

                # Retrieve all of the contours without establishing any hierarchical relationships (RETR_LIST)
                _, contours, hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

                # Initialize legos brick properties list and its length
                legos_properties_list = []
                legos_properties_list_length = 0

                # Loop over the contours
                for contour in contours:

                    # Compute contour moments, which include area,
                    # its centroid, and information about its orientation
                    moments_dict = cv2.moments(contour)

                    # Compute the centroid of the contour (cX, cY)
                    if moments_dict["m00"] != 0:
                        centroid_x = int((moments_dict["m10"] / moments_dict["m00"]))
                        centroid_y = int((moments_dict["m01"] / moments_dict["m00"]))

                        # Check if the contour is a lego brick
                        # Compute contour name and rotated bounding box of the found contour
                        # TODO: Error after libraries updating
                        contour_name, bbox = self.detect_lego_brick(contour, frame)

                        # If if the contour name is computed (square or rectangle),
                        # it means the contour has a shape and size of lego brick
                        if contour_name != "shape":

                            # Check color of the lego brick (currently only red and blue accepted)
                            color_name = self.check_color(centroid_x, centroid_y, color_image)

                            # Eliminate very small contours
                            if color_name != "wrongColor" and cv2.contourArea(contour) > MIN_AREA:

                                # Draw green lego bricks contours
                                cv2.drawContours(frame, [contour], -1, (0, 255, 0), 3)

                                logger.debug("Bounding box: {}".format(bbox))
                                logger.debug("Center coordinates: {}, {}".format(centroid_x, centroid_y))
                                logger.debug("Area: {}".format(cv2.contourArea(contour)))

                                # Update the properties list of all lego bricks which are found in the frame
                                legos_properties_list.append((centroid_x, centroid_y, contour_name, color_name))
                                legos_properties_list_length += 1

                # Log all objects with properties
                logger.debug("All saved objects with properties:")
                for lego_brick in legos_properties_list:
                    logger.debug(lego_brick)

                # TODO: planned to return objects
                # Compute tracked lego bricks dictionary
                # using the centroid tracker and set of properties
                tracked_lego_bricks_dict = \
                    self.centroid_tracker.update(legos_properties_list, legos_properties_list_length)

                # Loop over the tracked objects
                for (ID, tracked_lego_brick) in tracked_lego_bricks_dict.items():

                    # Draw green lego bricks IDs
                    text = "ID {}".format(ID)
                    cv2.putText(frame, text, (tracked_lego_brick[0][0] - 10, tracked_lego_brick[0][1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                    # Draw green lego bricks contour names
                    cv2.putText(frame, tracked_lego_brick[1], (tracked_lego_brick[0][0], tracked_lego_brick[0][1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                    # Draw green lego bricks centroid points
                    cv2.circle(frame, (tracked_lego_brick[0][0], tracked_lego_brick[0][1]), 4, (0, 255, 0), -1)

                    logger.debug("Detection: {}, {}".format(ID, tracked_lego_brick))
                    # Calculate coordinates, but not every frame, only when saving in JSON
                    # item[0] = calculate_coordinates(board_size, item[0])
                    # logger.debug("Detection recalculated:", ID, item)

                # TODO: work with objects
                # HTTP request with a new object
                # http://127.0.0.1:8000/assetpos/create/1/10.0/10.0
                # ID von Instanz in Response: assetpos_id: z.B. 5
                # lego_id = requests.get("http://127.0.0.1:8000/assetpos/create/"+lego_type+"/"+lego_pos_x+"/"+lego_pos_y)
                # TODO: Position updaten: http://127.0.0.1:8000/assetpos/set/5/15.0/10.0

                # Write the frame into the file 'output.avi'
                if record_video:
                    video_handler.write(frame)

                # Render shape detection images
                cv2.namedWindow('Shape detection', cv2.WINDOW_AUTOSIZE)
                cv2.imshow('Shape detection', frame)
                cv2.waitKey(1)

        finally:
            if record_video:
                video_handler.release()
            # Stop streaming
            self.pipeline.stop()


# Example usage is run if file is executed directly
if __name__ == '__main__':
    my_shape_detector = ShapeDetector()
    my_shape_detector.run()
