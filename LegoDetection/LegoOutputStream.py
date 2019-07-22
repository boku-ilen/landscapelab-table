from enum import Enum

import cv2
import config
import logging


# enable logger
from LegoBricks import LegoBrick

logger = logging.getLogger(__name__)

BRICK_LABEL_OFFSET = 10


class LegoOutputChannel(Enum):

    CHANNEL_SHAPE_DETECTION = 1
    CHANNEL_BOARD_DETECTION = 2
    CHANNEL_ROI = 3
    CHANNEL_COLOR = 4
    CHANNEL_CLIPPED_COLOR = 5
    CHANNEL_WHITE_BLACK = 6

    def next(self):
        value = self.value + 1
        if value > 6:
            value = 6
        return LegoOutputChannel(value)

    def prev(self):
        value = self.value - 1
        if value < 1:
            value = 1
        return LegoOutputChannel(value)


# this class handles the output video streams
class LegoOutputStream:

    WINDOW_NAME_DEBUG = 'DEBUG WINDOW'
    WINDOW_NAME_BEAMER = 'BEAMER WINDOW'

    def __init__(self, video_output_name=None, width=config.WIDTH, height=config.HEIGHT):

        self.active_channel = LegoOutputChannel.CHANNEL_COLOR
        self.active_window = LegoOutputStream.WINDOW_NAME_DEBUG  # TODO: implement window handling

        # create output windows
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_DEBUG, cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_BEAMER, cv2.WINDOW_AUTOSIZE)

        if video_output_name:
            # Define the codec and create VideoWriter object. The output is stored in .avi file.
            # Define the fps to be equal to 10. Also frame size is passed.
            self.video_handler = cv2.VideoWriter(video_output_name,
                                                 cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                                 10, (width, height))
        else:
            self.video_handler = None

    # Write the frame into the file
    def write_to_file(self, frame):
        # TODO: shouldn't we be able to select which channel we want to write to the file?
        if self.video_handler:
            self.video_handler.write(frame)

    # write the frame into a window
    def write_to_channel(self, channel, frame):
        # TODO: currently everything not written to the active channel is dropped
        if channel == self.active_channel:
            cv2.imshow(self.active_window, frame)

    # change the active channel, which is displayed in the window
    def set_active_channel(self, channel):
        self.active_channel = channel

    # mark the candidate in given frame
    @staticmethod
    def mark_candidates(frame, candidate_contour):
        cv2.drawContours(frame, [candidate_contour], -1, (0, 255, 0), 3)

    # we label the identified lego bricks in the stream
    @staticmethod
    def labeling(frame, tracked_lego_brick: LegoBrick):

        # FIXME: extract constants! and change array  [][] access into named attribute access
        # Draw green lego bricks IDs
        text = "ID {}".format(tracked_lego_brick.asset_id)
        tracked_lego_brick_position = tracked_lego_brick.centroid_x, tracked_lego_brick.centroid_y
        cv2.putText(frame, text, (tracked_lego_brick.centroid_x - BRICK_LABEL_OFFSET,
                                  tracked_lego_brick.centroid_y - BRICK_LABEL_OFFSET),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Draw green lego bricks contour names
        # FIXME: put other other caption like id of the lego brick
        cv2.putText(frame, tracked_lego_brick.status.name, tracked_lego_brick_position,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Draw green lego bricks centroid points
        cv2.circle(frame, tracked_lego_brick_position, 4, (0, 255, 0), -1)

    def update(self) -> bool:
        key = cv2.waitKeyEx(1)

        # simple switch of the channel
        if key == 97:  # 'a'
            logger.info("changed active channel one up")
            self.set_active_channel(self.active_channel.next())
        if key == 113:  # 'q'
            logger.info("changed active channel one down")
            self.set_active_channel(self.active_channel.prev())

        # Break with Esc  # FIXME: CG: keyboard might not be available - use signals?
        if key == 27:
            return True
        else:
            return False

    # closing the outputstream if it is defined
    def close(self):
        cv2.destroyAllWindows()
        if self.video_handler:
            self.video_handler.release()
