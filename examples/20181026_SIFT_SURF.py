# source: https://docs.opencv.org/3.4.0/df/dd2/tutorial_py_surf_intro.html

import cv2
import matplotlib.pyplot as plt

img = cv2.imread('./images/bespielLego2.JPG',0) #cv2.IMREAD_GRAYSCALE

# Create SURF object. You can specify params here or later.
# Here I set Hessian Threshold to 400
# surf = cv2.SURF(400) # not supported anymore
sift = cv2.xfeatures2d.SIFT_create()
surf = cv2.xfeatures2d.SURF_create()

orb = cv2.ORB_create(nfeatures=1500)

keypoints, descriptors = orb.detectAndCompute(img, None)

img = cv2.drawKeypoints(img, keypoints, None)

cv2.imshow("Image", img)
cv2.waitKey(0)
cv2.destroyAllWindows()

img2 = cv2.drawKeypoints(img,keypoints,None,(255,0,0),4)

plt.imshow(img2), plt.show()