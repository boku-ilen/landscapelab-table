# sources:
# https://www.pyimagesearch.com/2016/02/08/opencv-shape-detection/
# https://stackoverflow.com/questions/51347194/convert-white-pixels-to-black-in-opencv-python

from pyimagesearch.shapedetector import ShapeDetector
import imutils
import cv2

VIDEO = './videos/29s.mp4'

# initialize the camera or video
cap = cv2.VideoCapture(VIDEO)

while cap.isOpened():
    # capture and resize frame by frame
    ret, frame = cap.read()

    if ret:
        # TODO: find the whiteboard and crop to it
        crop_frame = frame[50:1000, 445:1590]
        # resize
        frame = imutils.resize(crop_frame, width=1000)

        # convert the resized image to grayscale
        img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # finding contours is like finding white object from black background
        # change whiteboard to black
        thresh = cv2.threshold(img_gray, 140, 255, cv2.THRESH_BINARY)[1]
        frame[thresh == 255] = 0
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        erosion = cv2.erode(frame, kernel, iterations=1)

        # optional whiteboard to black using HLS
        # imgHLS = cv2.cvtColor(frame, cv2.COLOR_BGR2HLS)
        # l_channel = imgHLS[:, :, 1]
        # mask = cv2.inRange(l_channel, 150, 255)
        # frame[mask == 255] = 0

        # convert the resized image to grayscale, blur it slightly, and threshold it
        img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(img_gray, (5, 5), 0)
        thresh = cv2.threshold(blurred, 55, 255, cv2.THRESH_BINARY)[1]

        # find contours in the thresholded image and initialize the shape detector
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]
        sd = ShapeDetector()

        # loop over the contours
        for c in cnts:
            # compute the center of the contour, then detect the name of the shape using only the contour
            M = cv2.moments(c)
            if M["m00"] != 0:
                cX = int((M["m10"] / M["m00"]))
                cY = int((M["m01"] / M["m00"]))
                shape = sd.detect(c)
                if shape != 'shape':
                    cv2.drawContours(frame, [c], -1, (0, 255, 0), 3)
                    cv2.putText(frame, shape, (cX, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # show the frame
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break
    # Break the loop
    else:
        break

cap.release()
cv2.destroyAllWindows()
