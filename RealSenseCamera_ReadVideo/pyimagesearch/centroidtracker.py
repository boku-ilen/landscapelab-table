# Source: https://www.pyimagesearch.com/2018/07/23/simple-object-tracking-with-opencv/
# TODO: to improve
# Add parameters: color, shape and use them to differ objects

# Dict subclass that remembers the order entries were added
from collections import OrderedDict
from scipy.spatial import distance as dist
import numpy as np


class CentroidTracker():
	def __init__(self, maxDisappeared=50):
		"""Initialize the next unique object ID with two ordered dictionaries"""
		self.nextObjectID = 0
		self.objects = OrderedDict()
		self.disappeared = OrderedDict()

		# Number of maximum consecutive frames a given object is allowed to be marked as "disappeared"
		self.maxDisappeared = maxDisappeared

	def register(self, centroid):
		"""When registering an object use the next available object ID to store the centroid"""
		self.objects[self.nextObjectID] = centroid
		self.disappeared[self.nextObjectID] = 0
		self.nextObjectID += 1

	def deregister(self, objectID):
		"""When deregistering an object ID delete the object ID from both of dictionaries"""
		del self.objects[objectID]
		del self.disappeared[objectID]

	def update(self, rects):
		"""Update position of the object"""
		# Check if the list of input bounding box rectangles is empty
		if len(rects) == 0:
			# Loop over any existing tracked objects and mark them as disappeared
			for objectID in self.disappeared.keys():
				self.disappeared[objectID] += 1

				# Deregister, if a maximum number of consecutive frames is reached
				if self.disappeared[objectID] > self.maxDisappeared:
					self.deregister(objectID)

			# Return early as there are no centroids or tracking info to update
			return self.objects

		# Initialize an array of input centroids for the current frame
		inputCentroids = np.zeros((len(rects), 2), dtype="int")

		# Loop over the bounding box rectangles
		for (i, (startX, startY, endX, endY)) in enumerate(rects):
			# Use the bounding box coordinates to derive the centroid
			cX = int((startX + endX) / 2.0)
			cY = int((startY + endY) / 2.0)
			inputCentroids[i] = (cX, cY)

		# If no objects are currently tracked take the input centroids and register each of them
		if len(self.objects) == 0:
			for i in range(0, len(inputCentroids)):
				self.register(inputCentroids[i])
		# Otherwise try to match the input centroids to existing object centroids
		else:
			# Grab the set of object IDs and corresponding centroids
			objectIDs = list(self.objects.keys())
			objectCentroids = list(self.objects.values())

			# Compute the distance between each pair of object centroids and input centroids
			# Goal is to match an input centroid to an existing object centroid
			# The output array shape of the distance map D will be (# of object centroids, # of input centroids)
			D = dist.cdist(np.array(objectCentroids), inputCentroids)

			# Sort the row indexes based on their minimum values
			rows = D.min(axis=1).argsort()

			# Find the smallest value in each column and sort the columns indexes based on the ordered rows
			# Goal is to have the index values with the smallest corresponding distance at the front of the lists
			cols = D.argmin(axis=1)[rows]

			# Example:
			# >>> D = dist.cdist(objectCentroids, centroids)
			# >>> D
			# array([[0.82421549, 0.32755369, 0.33198071],
			#        [0.72642889, 0.72506609, 0.17058938]])
			# >>> D.min(axis=1)
			# array([0.32755369, 0.17058938])
			# >>> rows = D.min(axis=1).argsort()
			# >>> rows
			# array([1, 0])

			# Use the distances to see if object IDs can be associated
			# Keep track of which of the rows and column indexes we have already examined (contains only unique values)
			usedRows = set()
			usedCols = set()

			# Update object centroids
			# Loop over the combination of the (row, column) index tuples
			for (row, col) in zip(rows, cols):
				# If the row or column value examined before, ignore it value
				if row in usedRows or col in usedCols:
					continue
				# Otherwise the found input centroid has the smallest Euclidean distance to an existing centroid
				# and has not been matched with any other object, so it will be set as a new centroid
				# Grab the object ID for the current row, set its new centroid, and reset the disappeared counter
				objectID = objectIDs[row]
				self.objects[objectID] = inputCentroids[col]
				self.disappeared[objectID] = 0

				# Indicate that we have examined each of the row and column indexes
				usedRows.add(row)
				usedCols.add(col)

			# Compute both the row and column index which have been not yet examined
			unusedRows = set(range(0, D.shape[0])).difference(usedRows)
			unusedCols = set(range(0, D.shape[1])).difference(usedCols)

			# If the number of object centroids is equal or greater than the number of input centroids
			# check if some of these objects have potentially disappeared
			if D.shape[0] >= D.shape[1]:
				# Loop over the unused row indexes
				for row in unusedRows:
					# Grab the object ID for the corresponding row index and increment the disappeared counter
					objectID = objectIDs[row]
					self.disappeared[objectID] += 1

					# Check if the number of consecutive frames the object has been marked "disappeared"
					if self.disappeared[objectID] > self.maxDisappeared:
						self.deregister(objectID)

			# Otherwise, register each new input centroid as a trackable object
			else:
				for col in unusedCols:
					self.register(inputCentroids[col])

		# Return the set of trackable objects
		return self.objects
