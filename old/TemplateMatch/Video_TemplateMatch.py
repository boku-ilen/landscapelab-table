import cv2
import numpy as np
import colorsys

# to be set
VIDEO = './videos/29s.mp4'
TEMPLATE = './images/legoBlue_50.jpg'
RESCALE = 1 # set 1 to rescale the size of video and template
SCALE = 60
THRESHOLD = 0.83
DISTANCE = 10 # must be more than DISTANCE px between found positions
BLUE_MIN = (0.55, 0.33, 141)
BLUE_MAX = (0.65, 1, 255)
RED_MIN = (0.92, 0.33, 200)
RED_MAX = (1, 1, 255)
SAVE_VIDEO = 0
# or define the lower and upper boundaries of the colors in the HSV color space
# LOWER = {'red': (0.92, 0.33, 200), 'blue': (0.55, 0.33, 141)}
# UPPER = {'red': (1, 1, 255), 'blue': (0.65, 1, 255)}
# define standard colors for circle around the object
# COLORS = {'red': (0, 0, 255), 'green': (0, 255, 0), 'blue': (255, 0, 0)}


# resize frame or template for efficiency/testing purposes
def rescale(image, w, h, if_template):
    percent = SCALE
    # test object recognition with template of different size
    # if if_template == 1:
    #    percent = int(percent - 4)
    w = int(w * percent/100)
    h = int(h * percent/100)
    return cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)


# get the HSV from RGB value
def get_colorHSV(image, w, h):
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(image)
    top_left = max_loc
    color = cv2.mean(image[top_left[1]:top_left[1] + h, top_left[0]:top_left[0] + w])
    # print(color[2], color[1], color[0]) # RGB
    return colorsys.rgb_to_hsv(color[2], color[1], color[0])


# get position of found templates and save without duplicates in a single frame
def find_single_position(array, element):
    # duplicate if located closer than given distance in both directions
    distance = DISTANCE
    if not array:
        array.append(element)
    else:
        for idx in range(len(array)):
            if -distance < element[0] - array[idx][0] < distance and -distance < element[1] - array[idx][1] < distance:
                break
            if idx == len(array) - 1:
                array.append(element)


# initialize the camera or video
cap = cv2.VideoCapture(VIDEO)

# set template
template = cv2.imread(TEMPLATE, 0)
height_tem, width_tem = template.shape[:2]
print("template width: %d, height: %d" % (width_tem, height_tem))
if RESCALE == 1:
    template = rescale(template, width_tem, height_tem, if_template=1)
height_tem, width_tem = template.shape[:2]
print("templateResize width: %d, height: %d" % (width_tem, height_tem))
# print("templateColorHSV: ")
# print(get_colorHSV(template, width_tem, height_tem))

# do only if needed, testing
# rotate template by 45 degrees
# templateCenter = (width_tem/2, height_tem/2)
# M = cv2.getRotationMatrix2D(templateCenter, 45, 1.0)
# templateRotated = cv2.warpAffine(template, M, (width_tem, height_tem))

# get video size, fps
# fps = cap.get(cv2.CAP_PROP_FPS)
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
print("video width: %d, height: %d" % (width, height))

# Define the codec and create VideoWriter object.The output is stored in 'outpy.avi' file.
# Define the fps to be equal to 10. Also frame size is passed.
if SAVE_VIDEO == 1:
    out = cv2.VideoWriter('outpy.avi', cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 10, (int(width * SCALE/100), int(height * SCALE/100)))

# capture frames until video is completed
while cap.isOpened():
    # capture and resize frame by frame
    ret, frame = cap.read()
    if ret:
        if RESCALE == 1:
            frame = rescale(frame, width, height, if_template=0)

        img_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # match Template
        result = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        # result2 = cv2.matchTemplate(img_gray, templateRotated, cv2.TM_CCOEFF_NORMED)

        locations = np.where(result >= THRESHOLD)
        # if templateRotated used:
        # locations = np.where((result >= threshold) | (result2 >= THRESHOLD))

        # example of print(locations):
        # (array([ x1, x2, ... ], dtype=int64), array([ y1, y2, ...], dtype=int64))

        legosBlue = []
        legosRed = []
        single_locations = []

        # save found locations (left-top) without duplicates in single frame
        # the * operator unpacks arguments in a function invocation statement
        for loc in zip(*locations[::-1]):
            find_single_position(single_locations, loc)
        # print(single_locations)

        mid_h_start = int(height_tem / 3)
        mid_h_end = int(2 * height_tem / 3)
        mid_w_start = int(width_tem / 3)
        mid_w_end = int(2 * width_tem / 3)
        for loc in single_locations:
            # calculate the mean color (RGB) in the middle of the found template (without white space)
            color = cv2.mean(frame[loc[1] + mid_h_start:loc[1] + mid_h_end, loc[0] + mid_w_start:loc[0] + mid_w_end])
            # or calculate the mean color (RGB) for the whole found template
            # color = cv2.mean(frame[loc[1]:loc[1] + height_tem, loc[0]:loc[0] + width_tem])
            # print(color)

            colorHSV = colorsys.rgb_to_hsv(color[2], color[1], color[0])
            # print(colorHSV)

            # TODO: rewrite
            if BLUE_MIN <= colorHSV <= BLUE_MAX:
                cv2.rectangle(frame, (loc[0], loc[1]), (loc[0] + width_tem, loc[1] + height_tem), (255, 0, 0), 2)
                blue = [loc[0] + width_tem, loc[1] + height_tem]
                legosBlue.append(blue)

            if RED_MIN <= colorHSV <= RED_MAX:
                cv2.rectangle(frame, (loc[0], loc[1]), (loc[0] + width_tem, loc[1] + height_tem), (0, 0, 255), 2)
                red = [loc[0] + width_tem, loc[1] + height_tem]
                legosRed.append(red)

        print("Blue: ")
        print(legosBlue)
        print("Red: ")
        print(legosRed)

        # Write the frame into the file 'output.avi'
        if SAVE_VIDEO == 1:
            out.write(frame)

        # show the frame
        cv2.imshow("Frame", frame)
        key = cv2.waitKey(1) & 0xFF

        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break
    # Break the loop
    else:
        break

if SAVE_VIDEO == 1:
    out.release()
cap.release()
cv2.destroyAllWindows()
