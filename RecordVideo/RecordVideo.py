import numpy as np
import cv2
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

        # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
        # depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

        # Show color images
        cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
        cv2.imshow('RealSense', color_image)
        key = cv2.waitKey(33)

        # Save video and break with Esc
        if key == 27:
            print("Save video")
            break

finally:

    # Stop streaming
    pipeline.stop()
