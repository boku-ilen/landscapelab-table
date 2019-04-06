# Main source: opencv3 computer vision with python cookbook


import cv2
import numpy as np


class QRCodeDetector:
    """There are set three qr-code corner-markers in corners of the board.
    The aim is to crop processing to the area between those markers (rectified)."""

    def __init__(self):
        """Constructor"""
        pass

    @staticmethod
    def intersect(l1, l2):
        """Implement a function which finds the intersection point of two lines"""
        delta = np.array([l1[1] - l1[0], l2[1] - l2[0]]).astype(np.float32)
        # TODO: if delta != 0
        delta = 1 / delta
        delta[:, 0] *= -1
        b = np.matmul(delta, np.array([l1[0], l2[0]]).transpose())
        b = np.diagonal(b).astype(np.float32)
        res = cv2.solve(delta, b)
        return res[0], tuple(res[1].astype(np.int32).reshape(2))

    @staticmethod
    def rectify(image, corners, out_size):
        """Define a function which un-warps the perspective distortions by calculating the
        correspondence between four pairs of distorted and un-distorted points"""
        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = corners[0]
        rect[1] = corners[1]
        rect[2] = corners[2]
        rect[3] = corners[3]
        dst = np.array([[0, 0], [out_size[1] - 1, 0], [out_size[1] - 1, out_size[0] - 1], [0, out_size[0] - 1]], dtype = "float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        rectified = cv2.warpPerspective(image, M, out_size)

        return rectified

    def qr_code_outer_corners(self, image):
        """Create a function which finds the outer corners of the QR code"""

        outer_corners_found = False
        outer_corners = []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, contours, hierarchy = cv2.findContours(th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = []
        centers = []
        hierarchy = hierarchy.reshape((-1, 4))
        for i in range(hierarchy.shape[0]):
            i_next, i_prev, i_child, i_par = hierarchy[i]
            if all(v == -1 for v in hierarchy[i][:3]):
                if all(v == -1 for v in hierarchy[i_par][:2]):
                    ids = [i, i_par, hierarchy[i_par][3]]
                    corner_cnts = []
                    for id_ in ids:
                        cnt = contours[id_]
                        apprx = cv2.approxPolyDP(cnt, cv2.arcLength(cnt, True) * 0.1, True)
                        if len(apprx) == 4:
                            corner_cnts.append(apprx.reshape((4, -1)))
                    if len(corner_cnts) == 3:
                        cnts.append(corner_cnts)
                        all_pts = np.array(corner_cnts).reshape(-1, 2)
                        centers.append(np.mean(all_pts, 0))
        if len(centers) == 3:
            distances_between_pts = np.linalg.norm(np.roll(centers, 1, 0) - centers, axis=1)
            max_dist_id = np.argmax(distances_between_pts)
            index_diag_pt_1 = max_dist_id
            index_diag_pt_2 = (max_dist_id - 1) % len(centers)
            index_corner_pt = (len(centers) - 1)*len(centers) // 2 - index_diag_pt_1 - index_diag_pt_2
            middle_pt = 0.5 * (centers[index_diag_pt_1] + centers[index_diag_pt_2])
            i_ul_pt = np.argmax(np.linalg.norm(cnts[index_corner_pt][-1] - middle_pt,axis=1))
            ul_pt = cnts[index_corner_pt][-1][i_ul_pt]
            for i in [index_diag_pt_1, index_diag_pt_2]:
                corner_cnts = cnts[i]
                outer_cnt = corner_cnts[-1]
                distances_to_mp = np.linalg.norm(outer_cnt - middle_pt, axis=1)
                max_dist_id = np.argmax(distances_to_mp)
                vec_from_mid_to_diag = outer_cnt[max_dist_id] - middle_pt
                vec_from_mid_to_corner = ul_pt - middle_pt
                cross_prod = np.cross(vec_from_mid_to_corner, vec_from_mid_to_diag)
                diff_idx = 0
                if cross_prod > 0:
                    ur_pt = outer_cnt[max_dist_id]
                    ur_pt_2 = outer_cnt[(max_dist_id + 1) % len(outer_cnt)]
                else:
                    bl_pt = outer_cnt[max_dist_id]
                    bl_pt_2 = outer_cnt[(max_dist_id - 1) % len(outer_cnt)]
            ret, br_pt = self.intersect((bl_pt, bl_pt_2), (ur_pt, ur_pt_2))
            if ret == True:
                outer_corners_found = True
                outer_corners = [ul_pt, ur_pt, br_pt, bl_pt]
        return outer_corners_found, outer_corners

    @staticmethod
    def find_minmax(contours):
        x = []
        y = []
        for c in contours:
            x.append(c[0])
            y.append(c[1])
        return min(x), min(y), max(x), max(y)
