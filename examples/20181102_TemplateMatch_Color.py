import cv2
import numpy as np
from matplotlib import pyplot as plt
import colorsys

img_rgb = cv2.imread('./images/bespielLegoBlau.JPG')
img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
template = cv2.imread('./images/legoBlau_rgb.JPG',0)

# Get size of template and perform template matching
# All the 6 methods for comparison in a list
#methods = ['cv.TM_CCOEFF', 'cv.TM_CCOEFF_NORMED', 'cv.TM_CCORR',
#            'cv.TM_CCORR_NORMED', 'cv.TM_SQDIFF', 'cv.TM_SQDIFF_NORMED']
w, h = template.shape[::-1]
res = cv2.matchTemplate(img_gray,template,cv2.TM_CCOEFF_NORMED)

threshold = 0.55
loc = np.where(res >= threshold)
print(loc)

lower = {'red':(0, 100, 100), 'green':(50, 100, 100), 'blue':(140,50,50)}
upper = {'red':(10,255,255), 'green':(70,255,255), 'blue':(160,255,255)}
blau = ()
    # Get template location in image and get its mean color intensity
    print(pt)
    print(pt[0])
    print(pt[1])


    color = cv2.mean(img_rgb[pt[1]:pt[1] + int(h/2), pt[0]:pt[0] + int(w/2)]) # color in the middle of found template
    # color = cv2.mean(img_red[top_left[1]:top_left[1] + h, top_left[0]:top_left[0]+w])
    print(color)
    colorHSV = colorsys.rgb_to_hsv(color[2], color[1], color[0])
    print(colorHSV)

    if colorHSV[0] >= 140/255 and colorHSV[0] <= 160/255:
        cv2.rectangle(img_rgb, pt, (pt[0] + w, pt[1] + h), (0,0,255), 2)
    #  cv.rectangle(img,top_left, bottom_right, 255, 2)

cv2.imwrite('res.png',img_rgb)