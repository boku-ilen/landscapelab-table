import random
import time
from math import sqrt
from random import choices
from typing import Any, Sequence

import cv2
import numpy as np
from functools import reduce
import scipy.cluster.vq
from cv2 import Mat
from numpy import dtype, floating, integer, ndarray
from scipy.cluster.vq import kmeans2, whiten

from LabTable.Configurator import logger


def average_mats(input_mats):
    #mats = [im / 255.0 for im in input_mats]
    base_color = np.mean(input_mats, axis=0).astype('uint8')
    #base_color = reduce(lambda x, y: x + y, mats, np.zeros_like(mats[0])) / len(mats)
    #base_color = (base_color * 255.0).astype('uint8')
    return base_color

def hue_delta(a,b,wrap=255):
    if a > b:
        return min(float(a)-float(b), float(wrap)-float(b)+float(a))
    return min(float(b)-float(a),float(wrap)-float(a)+float(b))

def color_distance(a,b):
    #return (b[0] - a[0])**2 + (b[1] - a[1])**2 + (b[2] - a[2]) ** 2
    return sqrt((b[1] - a[1])**2 + (b[2] - a[2]) ** 2)

def fill_recursive(image, contours, hierarchy, start_index, color=(0,0,0)):
    current_index = start_index
    while current_index >= 0:
        cv2.fillPoly(image, [contours[current_index]], color, cv2.LINE_AA)
        if hierarchy[current_index][2] >= 0:
            fill_recursive(image, contours, hierarchy, hierarchy[current_index][2], color)
        current_index = hierarchy[current_index][0]

def ms(t):
    return f"{round(t*1000)}ms"

def mark_drawings(base_color, number_of_colors=None, sample_points = None):
    contour_base = base_color.copy()

    # erosion to make the lines sharper
    element = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3), (-1,-1))
    #contour_base = cv2.erode(contour_base, element)

    # conversion to grayscale
    simple_gray = cv2.cvtColor(contour_base, cv2.COLOR_BGR2GRAY)
    simple_gray = cv2.erode(simple_gray, element)
    simple_gray = simple_gray / 255.0
    # linear contrast doubling & clipping
    simple_gray = simple_gray * 2 - 1
    simple_gray = np.clip(simple_gray, 0, 1)

    simple_gray *= 255

    #simple_gray = cv2.erode(simple_gray, element)

    # adaptive threshold to extract lines from projector noise
    simple_gray = cv2.adaptiveThreshold(simple_gray.astype('uint8'), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 5)

    # morphological close operation to fix up broken lines
    struc_elem = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5),(-1,-1))
    simple_gray = cv2.dilate(simple_gray, struc_elem)
    simple_gray = cv2.erode(simple_gray, struc_elem)

    # mask out margins to exclude from detection
    margin_mask = np.zeros_like(simple_gray)
    cv2.rectangle(margin_mask, (int(simple_gray.shape[1] * 0.1), int(simple_gray.shape[0] * 0.1)), (int(simple_gray.shape[1] * 0.9), int(simple_gray.shape[0] * 0.9)), 255, -1)

    contour_ready = cv2.bitwise_and(simple_gray, simple_gray, mask=margin_mask)
    #contour_ready = simple_gray * margin_mask
    struc_elem = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3),(-1,-1))
    #drawing = np.zeros((contour_ready.shape[0], contour_ready.shape[1], 3), dtype=np.uint8)

    # contour detection
    contours, hierarchy = cv2.findContours(contour_ready, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_L1)
    plausibility = [contour_plausible(cv2.boundingRect(c), contour_ready) for c in contours]
    if hierarchy is None or len(contours) == 0:
        return [],[]
    hierarchy = hierarchy[0]

    filtered_contours = []
    new_indices = {}
    filtered_hierarchy = []
    for contour in range(len(contours)):
        if plausibility[contour]:
            filtered_contours.append(contours[contour])
            new_indices[contour] = len(filtered_contours) - 1

    for i in range(len(hierarchy)):
        if plausibility[i]:
            for j in range(len(hierarchy[i])):
                if hierarchy[i][j] != -1:
                    if plausibility[hierarchy[i][j]]:
                        hierarchy[i][j] = new_indices[hierarchy[i][j]]
                    else:
                        hierarchy[i][j] = -1

            filtered_hierarchy.append(hierarchy[i])
    contours = filtered_contours
    hierarchy = filtered_hierarchy

    depths = []
    last_parents = []
    colors = []

    # enlarge color areas for color detection
    contour_base = cv2.erode(contour_base, cv2.getStructuringElement(cv2.MORPH_RECT, (11,11),(-1,-1)))

    sample_locations = [[66,325],[66,448], [66,575]]
    if sample_points is not None:
        sample_locations = [[int(s[0] * contour_base.shape[0]), int(s[1] * contour_base.shape[1])] for s in sample_points]
    sample_means = []
    for loc in sample_locations[:number_of_colors]:
        mask = np.zeros_like(contour_ready)
        cv2.circle(mask, loc, 24, 1, -1)
        mask = cv2.bitwise_and(mask, mask, mask=simple_gray)
        #mask *= simple_gray
        bbox = (loc[0] - 24, loc[1] - 24, 48, 48)
        base = contour_base[bbox[1]:bbox[1] + bbox[3], bbox[0]:bbox[0] + bbox[2]]
        mask = mask[bbox[1]:bbox[1] + bbox[3], bbox[0]:bbox[0] + bbox[2]]
        mean = np.mean(base[mask.astype('bool')], axis=0)
        sample_means.append(cv2.cvtColor(np.uint8([[[mean[0], mean[1], mean[2]]]]), cv2.COLOR_RGB2Lab)[0][0])



    for i in range(len(contours)):
        # get color info
        mask = np.zeros(simple_gray.shape, np.uint8)
        cv2.fillPoly(mask, [contours[i]], 255) # full area
        #mask = ((mask * (contour_ready / 255)) * 255).astype('uint8') # lines in area only
        mask = cv2.bitwise_and(mask, mask, mask=contour_ready)
        bbox = cv2.boundingRect(contours[i])
        base = contour_base[bbox[1]:bbox[1]+bbox[3],bbox[0]:bbox[0]+bbox[2]]
        mask = mask[bbox[1]:bbox[1]+bbox[3],bbox[0]:bbox[0]+bbox[2]]


        #mean_col = cv2.mean(base, mask=mask)

        pixels = np.array([base[mask.astype('bool')]])
        #print(pixels)

        # CIELAB color space, since Euclidean distance corresponds better to perceptual distance
        pixels_lab = cv2.cvtColor(pixels, cv2.COLOR_RGB2Lab)
        #pixels_lab = cv2.cvtColor(np.uint8([[mean_col]]), cv2.COLOR_RGB2Lab)

        # multi sampling
        colors.append(random.choices(pixels_lab[0].astype('float64'), None, k=32))

        #logger.info(colors[-1])

    best_centroids = []
    best_label = []
    best_silhouette = -100
    color_starts = [0]
    all_color_points = colors[0]

    k = number_of_colors

    for points in colors[1:]:
        color_starts.append(len(all_color_points))
        all_color_points = np.concat((all_color_points, points))

    if k is None: # no number given, try to guess
        for k in range(2, min(len(contours), 10)):
            centroids, label = kmeans2(all_color_points, k)
            clusters = []
            for i,c in enumerate(centroids):
                clusters.append(np.array(range(len(all_color_points)))[label == i])
            # simplified silhouette scoring
            silhouette_sum = 0
            for cluster in range(k):
                for point in range(len(clusters[cluster])):

                    dist_sum = color_distance(centroids[cluster], all_color_points[clusters[cluster][point]])
                    centroid_distances = [(i, color_distance(centroid, all_color_points[clusters[cluster][point]])) for i, centroid in enumerate(centroids)]
                    closest = sorted(centroid_distances, key=lambda d: d[1])[1][0]

                    nearest_sum = centroid_distances[1][1]
                    silhouette_point = 0
                    if len(clusters[closest]) > 1 and len(clusters[cluster]) > 1:
                        silhouette_point = (nearest_sum - dist_sum) / max(nearest_sum, dist_sum)

                    silhouette_sum += silhouette_point
            silhouette_sum /= len(all_color_points)
            if abs(silhouette_sum - best_silhouette) < 0.1: # knee detection (basic)
                break
            if silhouette_sum > best_silhouette:

                best_silhouette = silhouette_sum
                best_centroids = centroids
                best_label = label

    class_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    col_ids = []
    drawings = []
    ids = []
    bounds = []
    resolution = []

    #logger.info(f"best k was {len(best_centroids)}")
    for i in range(len(contours)):
        # color assignment
        stop_index = len(all_color_points)
        if len(color_starts) > i + 1:
            stop_index = color_starts[i + 1]

        rgb = (255,0,255)

        if k is None:
            # per-bin count among samples in contour
            counts = np.bincount(best_label[color_starts[i]: stop_index])
            #logger.info(counts)

            # best candidate ~= most samples in bin
            best = sorted([(i,count)for i,count in enumerate(counts)],key=lambda c:c[1],reverse=True)[0][0]
            centroid = best_centroids[best]
            rgb = cv2.cvtColor(np.uint8([[centroid]]), cv2.COLOR_Lab2RGB)[0][0]
            col_ids.append(best)
        else:
            pts = all_color_points[color_starts[i]:stop_index]
            point_mean = np.mean(pts, axis=0)
            sample_distances = sorted([(i, color_distance(point_mean, s)) for i, s in enumerate(sample_means)],
                                      key=lambda t: t[1])

            rgb = class_colors[sample_distances[0][0]]
            col_ids.append(sample_distances[0][0])

        colors[i] = (float(rgb[0]), float(rgb[1]), float(rgb[2]))

    for i in range(len(contours)):
        # if hierarchy has no parent for contour
        if hierarchy[i][3] < 0:
            col_rgb = colors[i]
            drawing = np.zeros_like(contour_ready)
            children = [j for j,l in enumerate(hierarchy) if l[3] == i]
            if len(children) >= 2 or any(hierarchy[c][2] > 0 for c in children):
                # assumed to be a filled area
                cv2.fillPoly(drawing, pts=[contours[i]], color=255, lineType=cv2.LINE_AA)
            else:
                # fill outermost contour
                cv2.fillPoly(drawing, [contours[i]], 255, cv2.LINE_AA)
                # unfill everything inside
                fill_recursive(drawing, contours, hierarchy, hierarchy[i][2], 0)
            ids.append(col_ids[i])
            bbox = list(cv2.boundingRect(contours[i]))
            drawing = drawing[bbox[1]:bbox[1]+bbox[3],bbox[0]:bbox[0]+bbox[2]].astype("uint8")
            drawings.append(drawing.tobytes().hex())

            for c in range(len(bbox)):
                bbox[c] = bbox[c] / contour_ready.shape[1-(c % 2)]
            bounds.append(bbox)
            resolution.append([drawing.shape[1], drawing.shape[0]])


    return drawings, ids, bounds, resolution

def contour_plausible(bounding_box: Sequence[int],
                      contour_ready: Mat | ndarray[Any, dtype[integer[Any] | floating[Any]]]) -> Any:
    return contour_ready.shape[1] * 0.5 > bounding_box[2] > contour_ready.shape[1] * 0.01 and contour_ready.shape[0] * 0.5 > \
        bounding_box[3] > contour_ready.shape[0] * 0.01 \
        and bounding_box[0] > contour_ready.shape[1] * 0.1 and bounding_box[0] + bounding_box[2] < contour_ready.shape[1] * 0.9 \
        and bounding_box[1] > contour_ready.shape[0] * 0.1 and bounding_box[1] + bounding_box[3] < contour_ready.shape[0] * 0.9