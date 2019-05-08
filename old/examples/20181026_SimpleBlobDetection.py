#source: https://github.com/AhadCove/LegoBlobDetection

import cv2
import numpy as np

# Read in the image in grayscale
img = cv2.imread('./images/bespielLego.JPG', cv2.IMREAD_GRAYSCALE)

# Determine which openCV version were using
if cv2.__version__.startswith('2.'):
    detector = cv2.SimpleBlobDetector()
else:
    detector = cv2.SimpleBlobDetector_create()

# Detect the blobs in the image
keypoints = detector.detect(img)
print(len(keypoints))

# Draw detected keypoints as red circles
imgKeyPoints = cv2.drawKeypoints(img, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

height, width, channels = imgKeyPoints.shape
imgKeyPointsResize = cv2.resize(imgKeyPoints, (int(width/2), int(height/2)))

# Display found keypoints
cv2.imshow("Keypoints", imgKeyPointsResize)
cv2.waitKey(0)

cv2.destroyAllWindows()