import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)



class PenDetector:
    def __init__(self, config, board_detector):
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        aruco_params = cv2.aruco.DetectorParameters()
        aruco_params.useAruco3Detection = True
        aruco_params.perspectiveRemovePixelPerCell = 12
        aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_CONTOUR
        self.aruco_detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)
        self.smoothing_window_size = config.get("pen", "num_smoothing_frames")

        marker_size_mm = float(config.get("pen", "marker_size_mm"))
        obj_points = np.array([
            [-marker_size_mm / 2, marker_size_mm / 2, 0],
            [marker_size_mm / 2, marker_size_mm / 2, 0],
            [marker_size_mm / 2, -marker_size_mm / 2, 0],
            [-marker_size_mm / 2, -marker_size_mm / 2, 0],
        ])
        self.marker_positions = {}
        config_positions = config.get("pen", "marker_positions_by_id")
        self.marker_positions = {int(k):np.array(config_positions[k], dtype=np.float32) for k in config_positions.keys()}

        # intrinsic euler (applied r-p-y)
        config_rotations = config.get("pen", "marker_rotations_by_id")
        marker_rotations_euler = {int(k):[float(x) for x in config_rotations[k]] for k in config_rotations.keys()}
        # marker_rotations_euler = {
        #     2: [59.0, 0.0, 0.0],
        #     3: [59.0, 0.0, 90.0],
        #     4: [0.0, 0.0, 0.0],
        # }

        self.marker_points = {}
        deg_to_rad = 1.0 / 57.2957795131

        for marker_id in self.marker_positions.keys():
            rotation_angles = marker_rotations_euler[marker_id]
            new_pts = obj_points.copy()

            new_pts_roll = new_pts.copy()

            # roll
            new_pts_roll[:, 1] = (new_pts[:, 1] * np.cos(deg_to_rad * rotation_angles[0])
                                  - new_pts[:, 2] * np.sin(deg_to_rad * rotation_angles[0]))
            new_pts_roll[:, 2] = (new_pts[:, 1] * np.sin(deg_to_rad * rotation_angles[0])
                                  + new_pts[:, 2] * np.cos(deg_to_rad * rotation_angles[0]))

            new_pts_pitch = new_pts_roll.copy()

            # pitch
            new_pts_pitch[:, 0] = (new_pts_roll[:, 0] * np.cos(deg_to_rad * rotation_angles[1])
                                   + new_pts_roll[:, 2] * np.sin(deg_to_rad * rotation_angles[1]))
            new_pts_pitch[:, 2] = (new_pts_roll[:, 0] * np.sin(deg_to_rad * rotation_angles[1]) * (-1)
                                   + new_pts_roll[:, 2] * np.cos(deg_to_rad * rotation_angles[1]))

            new_pts_yaw = new_pts_pitch.copy()

            # yaw
            new_pts_yaw[:, 0] = (new_pts_pitch[:, 0] * np.cos(deg_to_rad * rotation_angles[2])
                                 - new_pts_pitch[:, 1] * np.sin(deg_to_rad * rotation_angles[2]))
            new_pts_yaw[:, 1] = (new_pts_pitch[:, 0] * np.sin(deg_to_rad * rotation_angles[2])
                                 + new_pts_pitch[:, 1] * np.cos(deg_to_rad * rotation_angles[2]))

            new_pts = new_pts_yaw
            # position relative to tip
            new_pts += self.marker_positions[marker_id]
            self.marker_points[marker_id] = new_pts

        self.camera_matrix = board_detector.camera_matrix
        self.dist_coeffs = board_detector.dist_coeffs
        self.board_detector = board_detector
        self.bypass = True
        self.smoothing_window = []
        self.pen_down_threshold = config.get("pen", "touch_activate_threshold")
        self.pen_up_threshold = config.get("pen", "touch_release_threshold")
    def detect_pen(self, img):
        if self.bypass:
            return None, False
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        #gray = img[:,:,2]
        #cv2.imshow("edges", gray)
        corners, ids, rejected = self.aruco_detector.detectMarkers(gray)
        positions = []
        for i in range(len(corners)):
            if ids[i][0] not in self.marker_points.keys(): continue
            for j in range(corners[i].shape[0]):
                betterCorner = cv2.cornerSubPix(gray, corners[i][j], (5, 5), (-1, -1),
                                                (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 120, 0.001))
                corners[i][j] = betterCorner
            solved, rvec, tvec = cv2.solvePnP(self.marker_points[ids[i][0]], corners[i], self.camera_matrix, self.dist_coeffs)
            if not solved:
                continue
            # solved, rvec, tvec = cv2.solvePnP(objPoints, corners[i], camera_matrix, dist_coeffs)
            # cv2.drawFrameAxes(img, camera_matrix, dist_coeffs, rvec, tvec, marker_size_mm, 5)
            estimated_center_obj = np.array([[0.0, 0.0, 0.0]])
            #estimated_center_obj = tvec.reshape((1,3,1))

            estimated_center_screen = cv2.projectPoints(estimated_center_obj, rvec, tvec, self.camera_matrix, self.dist_coeffs)[0]
            #estimated_center_screen = cv2.projectPoints(estimated_center_obj, rvec, tvec, np.eye(3), self.dist_coeffs)[0]
            estimated_center_screen = cv2.undistortImagePoints(estimated_center_screen, self.camera_matrix, self.dist_coeffs)
            estimated_center_screen[0][0][0] = np.clip(estimated_center_screen[0][0][0], 0, img.shape[1])
            estimated_center_screen[0][0][1] = np.clip(estimated_center_screen[0][0][1], 0, img.shape[0])
            board_pos = cv2.perspectiveTransform(estimated_center_screen, self.board_detector.perspective_matrix) / np.array([[[self.board_detector.board.width, self.board_detector.board.height]]]) - np.array([[[0.5,0.5]]])
            board_pos[0][0][1] *= self.board_detector.projection_height * -1
            board_pos[0][0][0] *= self.board_detector.projection_height * (self.board_detector.board.width / self.board_detector.board.height)
            #logger.info(board_pos)
            #dist_screen = np.matmul(cv2.Rodrigues(self.board_detector.aruco_transform[0])[0], np.array([[[-estimated_center_screen[0][0][0]], [-estimated_center_screen[0][0][1]], [0]]])).reshape((1,3))
            dist_screen = np.matmul(cv2.Rodrigues(self.board_detector.aruco_transform[0])[0], np.array([[[board_pos[0][0][0]], [board_pos[0][0][1]], [0]]])).reshape((1,3))
            dist_screen[0][2] += self.board_detector.aruco_transform[1][2][0]
            #logger.info(str(estimated_center_obj))
            distance = -(tvec.reshape((1,3))[0][2] - dist_screen[0][2])
            #logger.info(distance)

            if ids[i][0] != 1:
                clip_pos = (cv2.perspectiveTransform(estimated_center_screen, self.board_detector.perspective_matrix) / np.array([[[self.board_detector.board.width, self.board_detector.board.height]]]))[0][0]
                positions.append([clip_pos[0], clip_pos[1], distance])
        if len(positions) > 0:
            mean_pos = np.median(np.array(positions), axis=0).tolist()
            self.smoothing_window.append(mean_pos)
            if len(self.smoothing_window) > self.smoothing_window_size:
                self.smoothing_window = self.smoothing_window[-self.smoothing_window_size:]
            return np.median(np.array(self.smoothing_window), axis=0).tolist(), True
        return None, False
