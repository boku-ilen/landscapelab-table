# main source: https://www.kaggle.com/wesamelshamy/tutorial-image-feature-extraction-and-matching
# Oriented FAST and Rotated BRIEF (ORB) for feature detection and description.
# This algorithm was developed and implemented by OpenCV Labs, and it's part of their OpenCV library for computer vision

import numpy as np
import pandas as pd
import cv2
import matplotlib.pyplot as plt
import os

QUERY_IMAGE = './images/board.png'
TRAIN_IMAGE = './images/legoBlau_rgb.JPG'


# Detect and compute interest points and their descriptors
def image_detect_and_compute(detector, img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kp, des = detector.detectAndCompute(img, None)
    return img, kp, des


# Draw ORB feature matches of the given two images
# TODO: replace n matches with treshold
def draw_image_matches(detector, img1_name, img2_name, nmatches=10):
    img1, kp1, des1 = image_detect_and_compute(detector, img1_name)
    img2, kp2, des2 = image_detect_and_compute(detector, img2_name)

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    matches = sorted(matches, key=lambda x: x.distance)  # Sort matches by distance.  Best come first.

    img_matches = cv2.drawMatches(img1, kp1, img2, kp2, matches[:nmatches], img2, flags=2)  # Show top 10 matches
    plt.figure(figsize=(16, 16))
    plt.title('ORB matches')
    plt.imshow(img_matches)
    plt.show()


queryImage = cv2.imread(QUERY_IMAGE)
trainImage = cv2.imread(TRAIN_IMAGE)

# TODO: find the whiteboard and crop to it
queryImage = queryImage[50:1000, 445:1590]

# Convert from cv's BRG default color order to RGB
queryImage = cv2.cvtColor(queryImage, cv2.COLOR_BGR2RGB)
trainImage = cv2.cvtColor(trainImage, cv2.COLOR_BGR2RGB)

# OpenCV 3 backward incompatibility: Do not create a detector with `cv2.ORB()`
orb = cv2.ORB_create()
key_points, description = orb.detectAndCompute(queryImage, None)

# Draw circles on found interest points/features
queryImage_keypoints = cv2.drawKeypoints(queryImage, key_points, queryImage, flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
plt.figure(figsize=(16, 16))
plt.title('ORB Interest Points')
plt.imshow(queryImage_keypoints)
plt.show()

orb = cv2.ORB_create()
# Draw ORB feature matches of the given two images
draw_image_matches(orb, queryImage, trainImage)
