import json
import os
import subprocess
from sys import path

import cv2
import sys
import numpy as np

if not __name__ == "__main__":
    exit(1)

def linux_set_cam_option(option_name, value, device):
    subprocess.run(["v4l2-ctl", "-d", str(device), "-c", f"{option_name}={value}"])

config_file = os.path.join(os.getcwd(), "table-config.json")
config_dict = json.loads(open(config_file, "r").read())

resolution = (int(config_dict["video_resolution"]["width"]), int(config_dict["video_resolution"]["height"]))#(3840, 2160)
cam_idx = int(config_dict["camera"]["opencv_device_nr"])

camera = cv2.VideoCapture(cam_idx, cv2.CAP_V4L2)
camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))
camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
camera.set(cv2.CAP_PROP_FPS, int(config_dict["video_resolution"]["framerate"]))
cam_options = config_dict["camera"]["linux_options"]
if sys.platform == "linux" and False:
    for cam in cam_options:
        linux_set_cam_option(cam[0], cam[1], cam_idx)

    camera.set(cv2.CAP_PROP_ZOOM, int(config_dict["camera"]["opencv_zoom"]))
    camera.set(cv2.CAP_PROP_EXPOSURE, int(config_dict["camera"]["opencv_exposure"]))

board_size = (7,10)

done = False
print(camera.isOpened())

obj_points = np.zeros((board_size[0] * board_size[1], 3), np.float32)
obj_points[:,:2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape((-1,2)) * 19.0

cam_matrix = np.eye(3,3)
dist_coeffs = np.zeros((8,1))
try:
    with open("./params.json", "r") as paramfile:
        data_dict = json.load(paramfile)
        cam_matrix = np.array(data_dict["matrix"])
        dist_coeffs = np.array(data_dict["dist_coeffs"])
except:
    with open("./params.json", "x") as newfp:
        newfp.flush()
        newfp.close()
calibration_points = []
counter = 0
while not done:
    img_ok, img = camera.read()
    if not img_ok:
        print("not ok")
        cv2.waitKey(1)
        continue
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    #pts = detector.detect(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY))
    #cv2.drawKeypoints(img, pts, img, (255,0,0))


    cv2.imshow("current", cv2.resize(img, (1280, 720)))
    k = cv2.waitKey(1)
    counter += 1
    if counter > 20 and not k == ord('n'):
        found, points = cv2.findChessboardCornersSB(gray, board_size)
        if found:
            points = cv2.cornerSubPix(gray, points, (11,11),(-1,-1), (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
            img = cv2.drawChessboardCorners(img, board_size, points, found)
            calibration_points.append(points)
            print(f"SNAP {len(calibration_points)}")
            cv2.waitKey(100)
            counter = 0
    elif k == ord('n'):
        done = True

#np.array([obj_points for i in range(len(calibration_images))])
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(np.array([obj_points for i in range(len(calibration_points))]), calibration_points, resolution, cam_matrix, dist_coeffs)
print(ret, mtx, dist, rvecs, tvecs)

with open("./params.json", 'w+') as paramjson:
    paramjson.write(json.dumps({
        "matrix": mtx.tolist(),
        "dist_coeffs": dist.tolist()
    }))
cv2.destroyAllWindows()
while True:
    ok, img = camera.read()
    new_mtx = None
    cv2.imshow("original", cv2.resize(img, (1280, 720)))
    img = cv2.undistort(img, mtx, dist)
    cv2.imshow("undistorted", cv2.resize(img, (1280, 720)))

    if cv2.waitKey(1) == ord(' '):
        cv2.destroyAllWindows()
        break
