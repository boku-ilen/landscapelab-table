import cv2
import config


# this class handles the output video streams
class LegoOutputStream:

    WINDOW_NAME_SHAPE_DETECTION = 'Shape detection'
    WINDOW_NAME_COLOR = 'Color'
    WINDOW_NAME_ROI = 'Region of Interest'

    video_handler = None

    def __init__(self, video_output_name=None, width=config.WIDTH, height=config.HEIGHT):

        # create output windows
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_SHAPE_DETECTION, cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_COLOR, cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow(LegoOutputStream.WINDOW_NAME_ROI, cv2.WINDOW_AUTOSIZE)

        if video_output_name:
            # Define the codec and create VideoWriter object. The output is stored in .avi file.
            # Define the fps to be equal to 10. Also frame size is passed.
            self.video_handler = cv2.VideoWriter(video_output_name,
                                                 cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                                                 10, (width, height))

    # Write the frame into the file
    def write_to_file(self, frame):
        if self.video_handler:
            self.video_handler.write(frame)

    # write the frame into a window
    @staticmethod
    def write_to_window(window, frame):
        cv2.imshow(window, frame)

    # mark the candidate in given frame
    @staticmethod
    def mark_candidates(frame, candidate_contour):
        cv2.drawContours(frame, [candidate_contour], -1, (0, 255, 0), 3)

    # we label the identified lego bricks in the stream
    @staticmethod
    def labeling(frame, tracked_lego_brick):

        # FIXME: extract constants! and change array  [][] access into named attribute access
        # Draw green lego bricks IDs
        text = "ID {}".format(tracked_lego_brick.asset_id)
        tracked_lego_brick_position = tracked_lego_brick[0][0], tracked_lego_brick[0][1]
        cv2.putText(frame, text, (tracked_lego_brick[0][0] - 10, tracked_lego_brick[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Draw green lego bricks contour names
        cv2.putText(frame, tracked_lego_brick[1], tracked_lego_brick_position,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Draw green lego bricks centroid points
        cv2.circle(frame, tracked_lego_brick_position, 4, (0, 255, 0), -1)

    @staticmethod
    def update() -> bool:
        key = cv2.waitKey(1)

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
