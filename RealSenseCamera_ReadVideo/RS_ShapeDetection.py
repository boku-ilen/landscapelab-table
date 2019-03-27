
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
import colorsys
import logging
import logging.config
import time
from QRCodeDetection.QRCodeDetection import QRCodeDetector
from Tracking.Tracker import Tracker
from Tracking.MyTracker import MyTracker


# configure logging
logger = logging.getLogger(__name__)
try:
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

MIN_AREA = 70


class ShapeDetector:

    # this is the centroid tracker instance
    centroid_tracker = None

    pipeline = None

    # the configuration instance of the realsense camera
    realsense_config = None

    depth_scale = None

    # Check if the shape is the searched object
    def detect(self, contour, frame):

        # Initialize the shape name and approximate the contour
        # with Douglas-Peucker algorithm
        shape = "shape"
        epsilon = 0.1 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Check if the shape has 4 vertices
        if len(approx) == 4:
            # Compute the rotated bounding box and draw all found objects (red)
            # For testing purposes, later should be computed only in the loop
            # and without drawing
            rect = cv2.minAreaRect(contour)  #TODO: was c
            box = np.int0(cv2.boxPoints(rect))
            cv2.drawContours(frame, [box], 0, (0, 0, 255), 2)

            # Compute the bounding box of the contour and the aspect ratio
            (x, y, w, h) = cv2.boundingRect(approx)
            bbox = (x, y, w, h)
            # cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # Check the size and color of the shape to decide if it is the searched object
            if (MIN_LENGTH < h < MAX_LENGTH) & (MIN_LENGTH < w < MAX_LENGTH):
                shape = self.check_if_square(box)
            return shape, bbox
        return shape, []

    # Check if square or rectangle
    def check_if_square(self, box):

        sides_length = self.calculate_size(box)

        # Compute the aspect ratio
        ar = int(sides_length[0]) / int(sides_length[1])
        shape = "shape"

        if MIN_SQ <= ar <= MAX_SQ:
            shape = "square"
            print("Square size:", sides_length[0], sides_length[1])
        elif MIN_REC < ar < MAX_REC:
            shape = "rectangle"
            print("Rectangle size:", sides_length[0], sides_length[1])

        return shape

    # Calculate two sides from one of corners
    @staticmethod
    def calculate_size(box):

        length = []
        # TODO comment
        for idx in range(3):
            length.append(np.linalg.norm(box[0] - box[idx+1]))

        # Delete the highest value (diagonal), only two sides lengths
        # are remaining in the array
        result = np.delete(length, np.argmax(length))
        return result

    # Return color name of the found object
    @staticmethod
    def check_color(x, y, color_image):

        # calculate the mean color (RGB)
        color = cv2.mean(color_image[y:y+4, x:x+4])

        colorHSV = colorsys.rgb_to_hsv(color[2], color[1], color[0])
        logger.debug("HSV:", colorHSV)

        result = "wrongColor"
        if RED_MIN[0] <= colorHSV[0] <= RED_MAX[0] \
                and RED_MIN[1] <= colorHSV[1] <= RED_MAX[1]\
                and RED_MIN[2] <= colorHSV[2] <= RED_MAX[2]:
            result = "red"

        elif BLUE_MIN[0] <= colorHSV[0] <= BLUE_MAX[0]\
                and BLUE_MIN[1] <= colorHSV[1] <= BLUE_MAX[1]\
                and BLUE_MIN[2] <= colorHSV[2] <= BLUE_MAX[2]:
            result = "blue"

        return result

    # TODO: (0, 1 000 000) or float
    # Return coordinates of the detected object for (min, max) = (0, 1000)
    # (0, 0) is the outer corner of the middle QR-Code marker
    @staticmethod
    def calculate_coordinates(board_size, coordinates, max=1000):
        return int(coordinates[0] * max / board_size), \
               int(coordinates[1] * max / board_size)

    def run(self, record_video=False):

        # Define the codec and create VideoWriter object.The output is stored in 'outpy.avi' file.
        # Define the fps to be equal to 10. Also frame size is passed.
        video_handler = None
        if record_video:
            video_handler = cv2.VideoWriter(VIDEO_FILE, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                            10, (int(WIDTH), int(HEIGHT)))

        # Initialize the clipping distance
        clip_dist = 0
        # Detection of the board with QR-Code Detector until the board found
        board_detected = False
        result = False
        board_size = HEIGHT
        middle_x = int(WIDTH/2)
        middle_y = int(HEIGHT/2)

        try:
            # main loop
            while True:

                t0 = time.time()
                # Wait for depth and color frames
                frames = self.pipeline.wait_for_frames()
                # Align the depth frame to color frame
                aligned_frames = self.alignment_stream.process(frames)
                # Get aligned frames
                aligned_depth_frame = aligned_frames.get_depth_frame()  # aligned_depth_frame is a 640x480 depth image
                color_frame = aligned_frames.get_color_frame()

                # ..
                logger.debug("!! new frame started at {}".format(t0))

                # Validate that both frames are valid
                if not aligned_depth_frame or not color_frame:
                    continue

                # Convert images to numpy arrays
                depth_image = np.asanyarray(aligned_depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())

                # Change background regarding clip_dist to black (depth image is 1 channel, color is 3 channels)
                depth_image_3d = np.dstack((depth_image, depth_image, depth_image))
                clipped_color_image = np.where(depth_image_3d > clip_dist * (1 + CLIP)
                                               or depth_image_3d < clip_dist * (1 - CLIP),
                                               0, color_image)

                # Set ROI as the color_image to set the same size
                region_of_interest = color_image
                # Set empty list of found objects

                # Show color image
                cv2.imshow('Color', color_image)

                # Get the distance to the board (the middle of the frame)
                if not clip_dist or not board_detected:
                    clip_dist = aligned_depth_frame.get_distance(middle_x, middle_y) / self.depth_scale
                    print("Distance to the table is:", clip_dist)

                # Detect the corners of the board, save position and eliminate perspective transformations (square)
                # The board must be square, markers should be placed precisely
                # TODO: if camera is lightly moving position must be updated
                if not board_detected:
                    print("Board detecting")
                    result, corners = self.qrcode_detector.qr_code_outer_corners(color_image)

                if result:
                    board_detected = True
                    if all((0, 0) < tuple(c) < (color_image.shape[1], color_image.shape[0]) for c in corners):
                        # print("Board:", corners)
                        # print("Distance to the table is:", clip_dist)
                        # Print corners coordinates
                        for contour in corners:
                            # print("Board corner:", c)
                            # Calculate board coordinates
                            minX, minY, maxX, maxY = self.qrcode_detector.find_minmax(contour)
                            board_size = maxX-minX
                            # print(board_size)

                        # Eliminate perspective transformations, change to square
                        rectified = self.qrcode_detector.rectify(clipped_color_image, corners, (board_size, board_size))
                        # Set ROI to black and add only the rectified board with searched objects
                        region_of_interest[0:HEIGHT, 0:WIDTH] = [0, 0, 0]
                        region_of_interest[0:board_size, 0:board_size] = rectified
                else:
                    region_of_interest[0:HEIGHT, 0:WIDTH] = [0, 0, 0]

                cv2.imshow('ROI', region_of_interest)
                frame = region_of_interest

                # Convert the image to grayscale
                img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Change whiteboard to black (contours are to find from black background)
                # TODO: use hierarchy to find contours without changing to black
                thresh = cv2.threshold(img_gray, 140, 255, cv2.THRESH_BINARY)[1]
                frame[thresh == 255] = 0
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
                erosion = cv2.erode(frame, kernel, iterations=1)

                # TODO: check if it helps
                # Trying to remove gray colors to ignore shadows
                frame_HSV = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                thresh = cv2.inRange(frame_HSV, (0, 0, 0), (255, 255, 120))
                frame[thresh == 255] = 0

                # Convert the resized image to grayscale, blur it slightly, and threshold it
                img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
                thresh = cv2.threshold(blurred, 55, 255, cv2.THRESH_BINARY)[1]

                # Find contours in the thresholded image
                contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                contours = contours[0]

                properties = []
                length = 0
                # Loop over the contours
                for contour in contours:
                    # compute the center of the contour (cX, cY) and detect whether it is the searched object
                    M = cv2.moments(contour)
                    if M["m00"] != 0:
                        cX = int((M["m10"] / M["m00"]))
                        cY = int((M["m01"] / M["m00"]))
                        shape, bbox = self.detect(contour)
                        if shape != "shape":
                            # Check color (currently only red and blue accepted)
                            checkColor = self.check_color(cX, cY, color_image)
                            # Eliminate very small contours
                            if checkColor != "wrongColor" and cv2.contourArea(contour) > MIN_AREA:
                                cv2.drawContours(frame, [contour], -1, (0, 255, 0), 3)
                                cv2.putText(frame, shape, (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                                print("Bounding box:", bbox)
                                print("Center coordinates:", cX, cY)
                                print("Area:", cv2.contourArea(contour))

                                # Update the properites/objects list
                                properties.append((cX, cY, shape, checkColor))
                                length += 1

                # Print all objects with properties
                print("All saved objects with properties:")
                for obj in properties:
                    print(obj)

                # Update the centroid tracker using the computed set of properties
                objects = self.centroid_tracker.update(properties, length)
                # Loop over the tracked objects
                for (ID, item) in objects.items():
                    # Draw both the ID of the object and the centroid of the object on the output frame
                    text = "ID {}".format(ID)
                    cv2.putText(frame, text, (item[0][0] - 10, item[0][1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    cv2.circle(frame, (item[0][0], item[0][1]), 4, (0, 255, 0), -1)
                    print("Detection:", ID, item)
                    # Calculate coordinates, but not every frame, only when saving in JSON
                    # item[0] = calculate_coordinates(board_size, item[0])
                    # print("Detection recalculated:", ID, item)

                # Write the frame into the file 'output.avi'
                if record_video:
                    video_handler.write(frame)

                # Prepare json to send
                # TODO: differ between new, delete, move

                # Render shape detection images
                cv2.namedWindow('Shape detection', cv2.WINDOW_AUTOSIZE)
                cv2.imshow('Shape detection', frame)
                cv2.waitKey(1)

        finally:
            if record_video:
                video_handler.release()
            # Stop streaming
            self.pipeline.stop()

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
        logger.debug("Depth Scale is: ", self.depth_scale)

        # Initialize board detection
        self.qrcode_detector = QRCodeDetector()

        # Initialize the centroid tracker
        self.centroid_tracker = Tracker()
        # centroid_tracker = MyTracker()


# example usage is run if file is executed directly
if __name__ == '__main__':
    my_shape_detector = ShapeDetector()
    my_shape_detector.run()
