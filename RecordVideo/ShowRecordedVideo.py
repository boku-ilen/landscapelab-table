import numpy as np
import cv2
# Used pyrealsense2 on License: Apache 2.0.
import pyrealsense2 as rs

realsense_config = rs.config()
rs.config.enable_device_from_file(realsense_config, "lego_detection_test.bag")
pipeline = rs.pipeline()
realsense_config.enable_all_streams()
pipeline.start(realsense_config)

# Create alignment primitive with color as its target stream:
alignment_stream = rs.align(rs.stream.color)

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

            # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
            depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

            # Stack both images horizontally
            # images = np.hstack((color_image, depth_colormap))

            # Show images
            cv2.namedWindow('RealSense', cv2.WINDOW_AUTOSIZE)
            cv2.imshow('RealSense', color_image)
            cv2.imshow('Depth', depth_colormap)
            key = cv2.waitKey(33)

            # Break with Esc
            if key == 27:
                break

finally:

    # Stop streaming
    pipeline.stop()
