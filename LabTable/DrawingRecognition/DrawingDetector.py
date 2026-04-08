import cv2
import numpy as np
from functools import reduce

def average_mats(input_mats):
    mats = [im / 255.0 for im in input_mats]
    base_color = reduce(lambda x, y: x + y, mats, np.zeros_like(mats[0])) / len(mats)
    base_color = (base_color * 255.0).astype('uint8')
    return base_color

def mark_drawings(base_color):
    contour_base = base_color.copy()

    # erosion to make the lines sharper
    element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3), (-1,-1))
    contour_base = cv2.erode(contour_base, element)

    # conversion to grayscale
    simple_gray = cv2.cvtColor(contour_base, cv2.COLOR_BGR2GRAY)
    simple_gray = cv2.erode(simple_gray, element)
    simple_gray = simple_gray / 255.0
    # linear contrast doubling & clipping
    simple_gray = simple_gray * 2 - 1
    simple_gray = np.clip(simple_gray, 0, 1)

    simple_gray *= 255

    simple_gray = cv2.dilate(simple_gray, element)

    # adaptive threshold to extract lines from projector noise
    simple_gray = cv2.adaptiveThreshold(simple_gray.astype('uint8'), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 6)

    # morphological close operation to fix up broken lines
    struc_elem = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5),(-1,-1))
    simple_gray = cv2.dilate(simple_gray, struc_elem)
    simple_gray = cv2.erode(simple_gray, struc_elem)


    contour_ready = simple_gray
    struc_elem = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3),(-1,-1))

    # contour detection
    contours, hierarchy = cv2.findContours(contour_ready, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    drawing = np.zeros((contour_ready.shape[0], contour_ready.shape[1], 3), dtype=np.uint8)

    hierarchy = hierarchy[0]

    depths = []
    last_parents = []

    for i in range(len(contours)):
        # find nesting depth and top-level parent (by our standards)
        parent = hierarchy[i][3]
        depth = 0
        last_parent = parent
        while parent > 0:
            bbox = cv2.boundingRect(contours[parent])
            if bbox[2] < contour_ready.shape[1] * 0.5 and bbox[3] < contour_ready.shape[0] * 0.5:
                # exclude implausible sizes (margins!)
                depth += 1
                last_parent = parent
            parent = hierarchy[parent][3]
        depths.append(depth)
        last_parents.append(last_parent)

    for i in range(len(contours)):
        bounding_box = cv2.boundingRect(contours[i])
        width = bounding_box[2]
        height = bounding_box[3]
        if width < contour_ready.shape[1] * 0.5 and height < contour_ready.shape[0] * 0.5 and depths[i] == 0:
            children = [j for j,l in enumerate(last_parents) if l == i]
            if len(children) >= 2 or any(depths[c] >= 2 for c in children):
                # assumed to be a filled area
                cv2.fillPoly(drawing, pts=[contours[i]], color=(255, 0, 0))
            else:
                cv2.fillPoly(drawing, [contours[i]], (0,255,0))
                # contour only, fill even-odd
                currChild =hierarchy[i][2]
                while currChild > 0:
                    # for all children according to hierarchy
                    cv2.fillPoly(drawing, pts=[contours[currChild]], color=(0,0,0))
                    currChild = hierarchy[currChild][0]

    return drawing