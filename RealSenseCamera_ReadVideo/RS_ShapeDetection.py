# TODO: information about Apache License?
# License: Apache 2.0. (pyrealsense2)

import pyrealsense2 as rs
import imutils
import numpy as np
import cv2


def detect(contour):
    # Initialize the shape name and approximate the contour with Douglas-Peucker algorithm
    shape = "shape"
    epsilon = 0.1 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)

    # Check if the shape has 4 vertices
    if len(approx) == 4:
        # Compute the bounding box of the contour and compute the aspect ratio
        (x, y, w, h) = cv2.boundingRect(approx)
        ar = w / float(h)

        # Check the size and color of the shape to decide if it is the searched object
        # TODO: find size of objects depend on distance to the board, check color
        if (8 < h < 22) & (8 < w < 22):
            # Check if it is a square or a rectangle
            if 0.7 <= ar <= 1.3:
                shape = "square"
            elif 0.4 < ar < 2.2:
                shape = "rectangle"
    return shape


# Configure depth and color streams
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# TODO : find the middle of the frame to take distance to the board
middleX = int(320)
middleY = int(240)
# Initialize the clipping distance
clip_dist = 0

# Create alignment primitive with color as its target stream:
align = rs.align(rs.stream.color)

# Start streaming
profile = pipeline.start(config)

# Getting the depth sensor's depth scale
depth_sensor = profile.get_device().first_depth_sensor()
depth_scale = depth_sensor.get_depth_scale()
print("Depth Scale is: ", depth_scale)

try:
    while True:
        # Wait for depth and color frames
        frames = pipeline.wait_for_frames()
        # Align the depth frame to color frame
        aligned_frames = align.process(frames)
        # Get aligned frames
        aligned_depth_frame = aligned_frames.get_depth_frame()  # aligned_depth_frame is a 640x480 depth image
        color_frame = aligned_frames.get_color_frame()
        # Validate that both frames are valid
        if not aligned_depth_frame or not color_frame:
            continue

        # Convert images to numpy arrays
        depth_image = np.asanyarray(aligned_depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Get the distance to the board (the middle of the frame)
        if clip_dist == 0:
            clip_dist = aligned_depth_frame.get_distance(middleX, middleY) / depth_scale
            print("Distance to the table is:", clip_dist)

        # Change background regarding clip_dist to black (depth image is 1 channel, color is 3 channels)
        depth_image_3d = np.dstack((depth_image, depth_image, depth_image))
        bg_removed = np.where((depth_image_3d > clip_dist * 1.1) | (depth_image_3d < clip_dist * 0.9), 0, color_image)

        # Render aligned images
        # depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)
        # images = np.hstack((bg_removed, depth_colormap))
        cv2.namedWindow('Aligned', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('Aligned', bg_removed)

        # Change the white board to black and find objects

        # TODO: to optimize find the whiteboard and crop to it
        # TODO: maybe not needed if clipping with depth information used
        # crop_frame = bg_removed[50:120, 435:600]

        frame = bg_removed

        # Convert the image to grayscale
        img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Change whiteboard to black (contours are to find from black background)
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
        contours = contours[0] if imutils.is_cv2() else contours[1]

        # Loop over the contours
        for c in contours:
            # compute the center of the contour (cX, cY) and detect whether it is the searched object
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int((M["m10"] / M["m00"]))
                cY = int((M["m01"] / M["m00"]))
                shape = detect(c)
                if shape != 'shape':
                    cv2.drawContours(frame, [c], -1, (0, 255, 0), 3)
                    cv2.putText(frame, shape, (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                    print(cX, cY)

        # Render shape detection images
        cv2.namedWindow('Shape detection', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('Shape detection', frame)
        cv2.waitKey(1)

finally:

    # Stop streaming
    pipeline.stop()
