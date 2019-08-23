# this class represents the board and holds related properties
class Board:

    # initialize a list with the board corners:
    # [top_left_corner, top_right_corner,
    # bottom_right_corner, bottom_left_corner]
    corners = None

    # initialize distance to the board from the camera
    distance = None

    def __init__(self):

        # initialize dimensions of the board
        self.width = 1
        self.height = 1
