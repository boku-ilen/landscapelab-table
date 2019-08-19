# Sample code to show how to subtract background and find qr-codes
# If used in the project, constants must be separated

import numpy as np
import cv2
import pyzbar.pyzbar as pyzbar
# Used pyrealsense2 on License: Apache 2.0.
import pyrealsense2 as rs

realsense_config = rs.config()
rs.config.enable_device_from_file(realsense_config, "white_board2.bag")
pipeline = rs.pipeline()
realsense_config.enable_all_streams()
pipeline.start(realsense_config)

# Create alignment primitive with color as its target stream:
alignment_stream = rs.align(rs.stream.color)


def look_for_codes(frame):

    # Invert image it to black in white
    looking_for_qr_code_image = 255 - frame
    cv2.imshow('black_white', looking_for_qr_code_image)

    # Find and display QR codes
    decoded_objects = pyzbar.decode(looking_for_qr_code_image)

    return decoded_objects


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


loop_number = 0
try:
        # Run main loop with video frames
        while True:

            # Wait for depth and color frames
            frames = pipeline.wait_for_frames()

            # Align the depth frame to color frame
            aligned_frames = alignment_stream.process(frames)

            # Get aligned frames (depth images)
            aligned_depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            # Validate that both frames are valid
            if not aligned_depth_frame or not color_frame:
                continue

            # Convert images to numpy arrays
            depth_image = np.asanyarray(aligned_depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # Save background
            if loop_number == 0:
                background = color_image.copy().astype("float")

            if loop_number < 10:

                # Update a running average
                cv2.accumulateWeighted(color_image, background, 0.5)
                loop_number = loop_number + 1

            # Subtract background
            diff = cv2.absdiff(color_image, background.astype("uint8"))
            diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            thre, diff = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            cv2.imshow("difference", diff)

            decoded_objects = look_for_codes(diff)
            display(color_image, decoded_objects)

            # Show images
            cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
            cv2.imshow('RealSense', color_image)
            key = cv2.waitKey(33)

            # Break with Esc
            if key == 27:
                break

finally:

    # Stop streaming
    pipeline.stop()

