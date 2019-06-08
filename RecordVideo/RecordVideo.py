import numpy as np
import cv2
import pyzbar.pyzbar as pyzbar
# Used pyrealsense2 on License: Apache 2.0.
import pyrealsense2 as rs

WIDTH = int(1280)
HEIGHT = int(720)

# Configure depth and color streams
pipeline = rs.pipeline()
realsense_config = rs.config()
realsense_config.enable_stream(rs.stream.depth, WIDTH, HEIGHT, rs.format.z16, 30)
realsense_config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, 30)

# Record stream (color and depth) to file
realsense_config.enable_record_to_file('lego_detection_test.bag')

# Create alignment primitive with color as its target stream:
alignment_stream = rs.align(rs.stream.color)

# Start streaming
profile = pipeline.start(realsense_config)

# Getting the depth sensor's depth scale
depth_sensor = profile.get_device().first_depth_sensor()
depth_scale = depth_sensor.get_depth_scale()


# Display barcode and QR code location
def display(frame, decoded_objects):

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

try:

    while True:

        # Wait for a coherent pair of frames: depth and color
        frames = pipeline.wait_for_frames()

        # Align the depth frame to color frame
        aligned_frames = alignment_stream.process(frames)

        # Get aligned frames (depth images)
        aligned_depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        if not aligned_depth_frame or not color_frame:
            continue

        # Convert images to numpy arrays
        # depth_image = np.asanyarray(aligned_depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        # Convert to black and white to find QR-Codes
        # Threshold image to white in black
        mask = cv2.inRange(color_image, (0, 0, 0), (230, 230, 230))
        white_in_black = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        # Invert image it to black in white
        looking_for_qr_code_image = 255 - white_in_black

        # Find and display QR codes
        decoded_objects = pyzbar.decode(looking_for_qr_code_image)
        display(looking_for_qr_code_image, decoded_objects)

        # Show color images
        cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('RealSense', color_image)

        # Show found QR-Codes
        cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('QR_Codes', looking_for_qr_code_image)

        key = cv2.waitKey(33)

        # Save video and break with Esc
        if key == 27:
            print("Save video")
            break

finally:

    # Stop streaming
    pipeline.stop()
