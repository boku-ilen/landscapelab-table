# main source: https://www.pyimagesearch.com/2016/02/08/opencv-shape-detection/
# import the necessary packages
import cv2


class ShapeDetector:
	def __init__(self):
		pass

	def detect(self, c):  # contour
		# initialize the shape name and approximate the contour
		shape = "unidentified"
		peri = cv2.arcLength(c, True)
		approx = cv2.approxPolyDP(c, 0.04 * peri, True)

		# if the shape has 4 vertices, it is either a square or
		# a rectangle
		if len(approx) == 4:
			# compute the bounding box of the contour and use the
			# bounding box to compute the aspect ratio
			(x, y, w, h) = cv2.boundingRect(approx)
			ar = w / float(h)

			# a square will have an aspect ratio that is approximately
			# equal to one, otherwise, the shape is a rectangle
			if 1.05 >= ar <= 0.95:
				shape = "rectangle"
			else:
				shape = "square"
		else:
			shape = "shape"

		# return the name of the shape
		return shape
