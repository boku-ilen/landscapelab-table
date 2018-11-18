import cv2
import numpy as np
import colorsys

# to be set
VIDEO = './videos/29s.mp4'
TEMPLATE = './images/legoBlue_50.JPG'
RESCALE = 1 # set 1 to rescale the size of video and template
SCALE = 60
THRESHOLD = 0.83
DISTANCE = 10 # must be more than DISTANCE px between found positions


# resize frame or template for efficiency/testing purposes
def rescale(image, w, h, if_frame):
    percent = SCALE
    #if if_frame == 0:
    #    percent = int(percent - 4)
    w = int(w * percent/100)
    h = int(h * percent/100)
    return cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)


# get the HSV value
def get_colorHSV(image, w, h):
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(image)
    top_left = max_loc
    color = cv2.mean(image[top_left[1]:top_left[1] + h, top_left[0]:top_left[0] + w])
    # print(color[2], color[1], color[0]) # RGB
    return colorsys.rgb_to_hsv(color[2], color[1], color[0])


def find_single_position(array, element):
    distance = DISTANCE
    for i in range(len(array)):
        if -distance < element[0] - array[i][0] < distance and -distance < element[1] - array[i][1] < distance:
            break
        if i == len(array) - 1:
            array.append(element)


# initialize the camera or video
cap = cv2.VideoCapture(VIDEO)

# set template
template = cv2.imread(TEMPLATE, 0)
h, w = template.shape[:2]
print("template width: %d, height: %d" % (w, h))
if RESCALE == 1:
    template = rescale(template, w, h, if_frame=0)
h, w = template.shape[:2]
print("templateResize width: %d, height: %d" % (w, h))
# print("templateColorHSV: ")
# print(get_colorHSV(template, w, h))

# do only if needed, testing
# rotate template by 45 degrees
# templateCenter = (w/2, h/2)
# M = cv2.getRotationMatrix2D(templateCenter, 45, 1.0)
# templateRotated = cv2.warpAffine(template, M, (w, h))

# get video size, fps
# fps = cap.get(cv2.CAP_PROP_FPS)
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
print("video width: %d, height: %d" % (width, height))

# capture frames until video is completed
while cap.isOpened():
    # capture and resize frame by frame
    ret, frame = cap.read()
    if RESCALE == 1:
        frame = rescale(frame, width, height, if_frame=1)

    if ret == True:

        img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # match Template
        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        # res2 = cv2.matchTemplate(img_gray, templateRotated, cv2.TM_CCOEFF_NORMED)

        loc = np.where(res >= THRESHOLD)
        # if templateRotated used
        # loc = np.where((res >= threshold) | (res2 >= THRESHOLD))

        legosBlue = []
        legosRed = []

        for pt in zip(*loc[::-1]):  # list loc[<start>:<stop>:<step>]
            # get mean color (RGB) of found template
            color = cv2.mean(frame[pt[1]:pt[1] + h, pt[0]:pt[0]+w])

            # print(color)
            colorHSV = colorsys.rgb_to_hsv(color[2], color[1], color[0])
            # print(colorHSV)

            # if blue TODO: to adapt
            if (0.55, 0.33, 141) <= colorHSV <= (0.65, 1, 255):
                cv2.rectangle(frame, pt, (pt[0] + w, pt[1] + h), (255, 0, 0), 2)
                blue = [pt[0] + w, pt[1] + h]

                if legosBlue == []:
                    legosBlue.append(blue)
                else:
                    find_single_position(legosBlue, blue)

            # if red TODO: to adapt
            if (0.92, 0.33, 200) <= colorHSV <= (1, 1, 255):
                cv2.rectangle(frame, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)
                red = [pt[0] + w, pt[1] + h]

                if legosRed == []:
                    legosRed.append(red)
                else:
                    find_single_position(legosRed, red)

            # if yellow TODO: to found
            # not found with the template
        print("Blue: ")
        print(legosBlue)
        print("Red: ")
        print(legosRed)

        # show the frame
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break
cap.release()
cv2.destroyAllWindows()
