from ConfigManager import ConfigManager, ConfigError
from typing import Dict, Tuple, Optional
import numpy as np
import logging
import cv2
import os

# enable logger
logger = logging.getLogger(__name__)


class ImageHandler:

    def __init__(self, config: ConfigManager):
        self.config = config

        self.resource_path = ConfigManager.reconstruct_path(
            os.getcwd(),
            self.config.get("resources", "relative-path")
        )

    def load_image(
            self,
            name: str,
            size: Optional[Tuple[int, int]] = None,
            relative_center: Optional[Tuple[float, float]] = None,
            center: Optional[Tuple[int, int]] = None
    ):
        image_dict = self.config.get("resources", name)

        # check that image has path
        if 'path' not in image_dict:
            err_msg = 'image has no path specified'
            logger.error(err_msg)
            raise ConfigError(err_msg)

        image_path = ConfigManager.reconstruct_path(self.resource_path, image_dict['path'])
        img = cv2.imread(image_path, -1)

        # resize if size is not None or size specified in config
        # also ensure size exists in image_dict
        if size:
            img = cv2.resize(img, size)
            image_dict["size"] = [0, 0]
            image_dict["size"][0], image_dict["size"][1] = size
        elif 'size' in image_dict:
            img = cv2.resize(img, (image_dict['size'][0], image_dict['size'][1]))
        else:
            image_dict["size"] = [0, 0]
            image_dict["size"][0] = img.shape[1]
            image_dict["size"][1] = img.shape[0]

        # overwrite center if defined in params
        if relative_center:
            rel_x, rel_y = relative_center
            image_dict['center'] = [int(rel_x * image_dict['size'][0]), int(rel_y * image_dict['size'][1])]
        if center:
            image_dict['center'] = center

        img = ImageHandler.ensure_alpha_channel(img)

        # add image to dictionary and return
        image_dict['image'] = img
        return image_dict

    # draws an image onto a given background
    # both images must have an alpha channel
    # while im_back is a simple np array im_top must be a dictionary containing the image
    # additional fields in im_top (e.g. center) will be considered in the drawing process
    # offset determines the x,y position of the image
    @staticmethod
    def img_on_background(im_back, im_top: Dict, offset: Tuple[int, int]):
        img = im_top['image']

        top_x, top_y = offset
        if 'center' in im_top:
            top_x -= im_top['center'][0]
            top_y -= im_top['center'][1]

        top_w = img.shape[1]
        top_h = img.shape[0]

        bac_w = im_back.shape[1]
        bac_h = im_back.shape[0]

        bac_start_x = min(max(0, top_x), bac_w)
        bac_start_y = min(max(0, top_y), bac_h)
        bac_end_x = max(min(bac_w, top_x + top_w), 0)
        bac_end_y = max(min(bac_h, top_y + top_h), 0)

        top_start_x = min(max(0, -top_x), top_w)
        top_start_y = min(max(0, -top_y), top_h)
        top_end_x = max(min(top_w, bac_w - top_x), 0)
        top_end_y = max(min(top_h, bac_h - top_y), 0)

        alpha = img[top_start_y:top_end_y, top_start_x:top_end_x, 3] / 255.0

        im_back[bac_start_y:bac_end_y, bac_start_x:bac_end_x, 0] = (1. - alpha) * im_back[bac_start_y:bac_end_y, bac_start_x:bac_end_x, 0] + alpha * img[top_start_y:top_end_y, top_start_x:top_end_x, 0]
        im_back[bac_start_y:bac_end_y, bac_start_x:bac_end_x, 1] = (1. - alpha) * im_back[bac_start_y:bac_end_y, bac_start_x:bac_end_x, 1] + alpha * img[top_start_y:top_end_y, top_start_x:top_end_x, 1]
        im_back[bac_start_y:bac_end_y, bac_start_x:bac_end_x, 2] = (1. - alpha) * im_back[bac_start_y:bac_end_y, bac_start_x:bac_end_x, 2] + alpha * img[top_start_y:top_end_y, top_start_x:top_end_x, 2]

        if im_back.shape[2] == 4:
            im_back[bac_start_y:bac_end_y, bac_start_x:bac_end_x, 3] = np.maximum(
                im_back[bac_start_y:bac_end_y, bac_start_x:bac_end_x, 3], alpha * 255)
            # NOTE unsure if correct alpha blending but results seem fine
        return im_back

    @staticmethod
    def ensure_alpha_channel(image):

        # add alpha channel if not already here
        if image.shape[2] == 3:
            b, g, r = cv2.split(image)
            a = np.ones(b.shape, dtype=b.dtype) * 255
            image = cv2.merge((b, g, r, a))

        return image
