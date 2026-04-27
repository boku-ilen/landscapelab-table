import json
import os
from enum import Enum

import cv2
import numpy as np
import math

import logging.config

from LabTable.Configurator import Configurator
from LabTable.DrawingRecognition.DrawingDetector import average_mats
from LabTable.ExtentTracker import ExtentTracker
from LabTable.Model.Extent import Extent
from LabTable.Model.Board import Board

# configure logging
logger = logging.getLogger(__name__)

class BoardDetectorStage(Enum):
    MARKER_DETECTION = 0
    CORNER_REFINEMENT = 1

# this class manages the extent to detect and reference the extent of
# the board related to the video stream
class BoardDetector:
    def __init__(self, config):

        self.config = config

        # Initialize the board
        self.board = Board()

        # Get the resolution from config file
        self.frame_width = self.config.get("video_resolution", "width")
        self.frame_height = self.config.get("video_resolution", "height")

        # get data relating to aruco dimensions
        self.projection_height = self.config.get("beamer_resolution", "screen_height_mm")
        self.aruco_size = self.config.get("camera", "aruco_height_fraction") * self.projection_height

        # get data about camera calibration
        calib_file = self.config.get("resources", "calibration_file")["path"]
        resources_path = self.config.get("resources", "relative_path")
        resources_path.insert(0, "..")
        self.resource_path = Configurator.reconstruct_path(os.path.dirname(__file__),
                                                           resources_path)
        calib_file_path = Configurator.reconstruct_path(self.resource_path, calib_file)

        with open(calib_file_path, "r") as calib_fp:
            calib_data = json.load(calib_fp)
            self.camera_matrix = np.array(calib_data["matrix"])
            self.dist_coeffs = np.array(calib_data["dist_coeffs"])
        self.undistort_map = None
        self.perspective_matrix = np.identity(4)

        self.current_loop = 0

        self.detect_corners_frames_number = 0

        self.stage = BoardDetectorStage.MARKER_DETECTION
        self.image_pts = np.array([])

        self.buffer = []
        self.skip = 10

    # Compute pythagoras value
    @staticmethod
    def pythagoras(value_x, value_y):

        value = math.sqrt(value_x ** 2 + value_y ** 2)

        # Return pythagoras value
        return value

    # Detect the board using one ArUco marker in the center
    def detect_board(self, color_image: cv2.Mat):

        if self.stage == BoardDetectorStage.MARKER_DETECTION:
            self.buffer.append(color_image)
            if len(self.buffer) < 3:
                return False
            if len(self.buffer) > 3:
                self.buffer = self.buffer[-3:]

            # initialize detector and image
            aruco_frame_gray = cv2.cvtColor(average_mats(self.buffer), cv2.COLOR_BGR2GRAY)
            aruco_detector = cv2.aruco.ArucoDetector(
                cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50),
                cv2.aruco.DetectorParameters())
            # real-world size of marker is derived from our one known dimension, projected image height
            screen_height = self.config.get("beamer_resolution", "screen_height_mm")
            marker_size_mm = screen_height * self.config.get("camera", "aruco_height_fraction")

            # corners in correct order - center is origin
            corner_ones = np.array([
                [-1,  1, 0],
                [ 1,  1, 0],
                [ 1, -1, 0],
                [-1, -1, 0],
            ], dtype=np.float32)

            # aruco marker outside corners in marker's space
            aruco_object_points = corner_ones * marker_size_mm * 0.5

            # outside corners of board in marker's space
            board_corners = corner_ones
            board_corners[:,0] *= (screen_height * (self.frame_width / self.frame_height)) * 0.5
            board_corners[:,1] *= screen_height * 0.5

            # marker detection
            corners, ids, _ = aruco_detector.detectMarkers(aruco_frame_gray)
            if ids is None:
                # no markers found
                return False
            for i in range(ids.shape[0]):
                if ids[i] != 0:
                    # aruco marker should have ID 0, otherwise it's probably noise
                    continue
                for j in range(corners[i].shape[0]):
                    # refine corners for better estimation
                    better_corner = cv2.cornerSubPix(aruco_frame_gray, corners[i][j], (5, 5), (-1, -1),
                                                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 40, 0.001))
                    corners[i][j] = better_corner

                # aruco pose estimation
                solved, rvec, tvec = cv2.solvePnP(aruco_object_points, corners[i], self.camera_matrix, self.dist_coeffs)
                if solved:
                    # board corners in screen space
                    self.image_pts, _ = cv2.projectPoints(board_corners, rvec, tvec, self.camera_matrix, self.dist_coeffs)


                    #self.image_pts = image_pts
                    self.stage = BoardDetectorStage.CORNER_REFINEMENT
                    self.buffer = []

        elif self.stage == BoardDetectorStage.CORNER_REFINEMENT:
            self.skip -= 1
            if self.skip > 0:
                cv2.waitKey(33)
                return False

            # since we do perspective correction on undistorted image, undistort the corner coords
            self.image_pts = cv2.undistortImagePoints(self.image_pts, self.camera_matrix, self.dist_coeffs)

            # corner refinement using monocolor frame to find real corners
            frame_channel = cv2.undistort(color_image, self.camera_matrix, self.dist_coeffs)[:,:,1]
            frame_channel = cv2.dilate(frame_channel, cv2.getStructuringElement(cv2.MORPH_RECT, (3,3), (-1,-1)), iterations=2)
            self.image_pts = cv2.cornerSubPix(frame_channel, self.image_pts, (40,40), (-1,-1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 40, 0.001))

            self.board.corners = [x[0] for x in self.image_pts.tolist()]

            self.compute_board_size(self.board.corners)

            # precalculate undistortion maps to speed up rectify()
            self.undistort_map = cv2.initUndistortRectifyMap(self.camera_matrix,
                                                             self.dist_coeffs,
                                                             np.identity(3),
                                                             self.camera_matrix,
                                                             (self.frame_width, self.frame_height),
                                                             cv2.CV_32FC1)

            # Save corners in a numpy array
            source_corners = np.array(self.board.corners, dtype="float32")

            # Construct destination points which will be used to map the board to a top-down view
            destination_corners = np.array([
                [0, 0],
                [self.board.width, 0],
                [self.board.width, self.board.height],
                [0, self.board.height]], dtype="float32")

            # Pre-calculate the perspective transform matrix
            self.perspective_matrix = cv2.getPerspectiveTransform(source_corners, destination_corners)
            #cv2.imshow("f", frame_channel)
            return True
        return False

    # Undistort and warp the frame perspective to a top-down view (rectangle with screen's aspect ratio)
    def rectify(self, image):
        return cv2.warpPerspective(
            cv2.remap(
                image,
                self.undistort_map[0],
                self.undistort_map[1],
                cv2.INTER_LINEAR
            ),
            self.perspective_matrix,
            (self.board.width, self.board.height)
        )


    # Compute board size and set in configs
    def compute_board_size(self, corners):

        # distance between horizontal corner pairs
        top_width = self.pythagoras(corners[1][0] - corners[0][0], corners[1][1] - corners[0][1])
        bottom_width = self.pythagoras(corners[2][0] - corners[3][0], corners[2][1] - corners[3][1])

        # Compute board size
        # assumption: width in middle approximately equals the mean of top and bottom
        self.board.width = int((top_width + bottom_width) / 2)
        # assumption: square pixels -> aspect ratio should be the same as screen resolution
        self.board.height = int((self.config.get("screen_resolution", "height")/self.config.get("screen_resolution", "width"))*self.board.width)

        ExtentTracker.get_instance().board = Extent.from_rectangle(0, 0, self.board.width, self.board.height)
        logger.info('board has been set to {}'.format(ExtentTracker.get_instance().board))