# Sample code to show how the contrast, brightness
# and white balance can be adjusted
# If used in the project, constants must be separated

import cv2 as cv
import numpy as np

img = cv.imread('test.png')
img_hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)


# White balance, the light source is assumed to be white
# https://stackoverflow.com/questions/46390779/automatic
# -white-balancing-with-grayworld-assumption
# https://pippin.gimp.org/image-processing/chapter-automaticadjustments.html
def white_balance(image):

    # Convert to CIE L*a*b* color space
    # L* for the luminance from black (0) to white (100)
    # a* from from -128 (a bluish green) to +127 (magenta)
    # b* from from -128 (blue) to +127 (yellow)
    result = cv.cvtColor(image, cv.COLOR_BGR2LAB)

    # Save average a and b values
    avg_a = np.average(result[:, :, 1])
    avg_b = np.average(result[:, :, 2])

    # Save L, a and b values
    L = result[:, :, 0]
    a = result[:, :, 1]
    b = result[:, :, 2]

    # Adjust a and b color values
    # scale the chroma distance shifted according to amount of
    # luminance. The 1.1 overshoot is because we cannot be sure
    # to have gotten the data in the first place.
    a = a - ((avg_a - 128) * (L / 255.0) * 1.1)
    b = b - ((avg_b - 128) * (L / 255.0) * 1.1)

    # Save adjusted values as a result
    result[:, :, 1] = a
    result[:, :, 2] = b

    # Convert back to BGR color space
    result = cv.cvtColor(result, cv.COLOR_LAB2BGR)

    return result


# Adjust brightness and contrast of the image
# https://stackoverflow.com/questions/39308030/how-do-i-increase
# -the-contrast-of-an-image-in-python-opencv/41075028
def apply_brightness_contrast(image, brightness=0, contrast=0):

    # Adjust brightness
    if brightness != 0:
        if brightness > 0:
            shadow = brightness
            highlight = 255
        else:
            shadow = 0
            highlight = 255 + brightness
        alpha_brightness = (highlight - shadow)/255
        gamma_brightness = shadow

        result = cv.addWeighted(image, alpha_brightness, image, 0, gamma_brightness)
    else:
        result = image.copy()

    # Adjust contrast
    if contrast != 0:
        f = 131*(contrast + 127)/(127*(131-contrast))
        alpha_contrast = f
        gamma_contrast = 127*(1-f)

        result = cv.addWeighted(result, alpha_contrast, result, 0, gamma_contrast)

    return result


def remap(v, min, max):

    result = ((v-min) * 255.0)/(max-min)
    return result


# Stretch BGR components
def stretch_bgr(image):

    result = image.copy()

    # Save min/max bgr values
    min_b = np.min(result[:, :, 0])
    max_b = np.max(result[:, :, 0])
    min_g = np.min(result[:, :, 1])
    max_g = np.max(result[:, :, 1])
    min_r = np.min(result[:, :, 2])
    max_r = np.max(result[:, :, 2])

    # TODO: rewrite without loops if possible
    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            result[y, x, 0] = remap(result[y, x, 0], min_b, max_b)
            result[y, x, 1] = remap(result[y, x, 1], min_g, max_g)
            result[y, x, 2] = remap(result[y, x, 2], min_r, max_r)

    return result


# FIXME: not working yet as supposed
def stretch_luminance(image):

    # Convert to CIE L*a*b* color space
    result = cv.cvtColor(image, cv.COLOR_BGR2LAB)

    # Save min/max L values
    min_l = np.min(result[:, :, 0])
    max_l = np.max(result[:, :, 0])

    # Stretch values
    for y in range(image.shape[0]):
        for x in range(image.shape[1]):
            result[y, x, 0] = ((result[y, x, 0] - min_l) * 100.0)/(max_l - min_l)

    return result


# TODO: automize finding parameters
contrasted = apply_brightness_contrast(img, 80, 80)
white_balance_output = np.hstack((img, white_balance(contrasted)))

stretch_bgr_output = np.hstack((img, stretch_bgr(img)))
# stretch_luminance_output = np.hstack((img, stretch_luminance(img)))

# Show output
# cv.imshow('Contrasted', contrasted)
cv.imshow('Balance', white_balance_output)
cv.imshow('Stretch_bgr', stretch_bgr_output)
# cv.imshow('Stretch_luminance', stretch_luminance_output)

cv.waitKey(0)
cv.destroyAllWindows()
