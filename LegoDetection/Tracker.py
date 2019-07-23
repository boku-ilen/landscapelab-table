import logging
import typing
from LegoBricks import LegoBrick, LegoStatus

# configure logging
logger = logging.getLogger(__name__)

MIN_DISTANCE = 6
MIN_APPEARED = 6
MAX_DISAPPEARED = 40


class Tracker:

    server_communicator = None
    tracked_candidates = {}  # we hold candidates which are not confirmed yet for some ticks
    confirmed_bricks: typing.List[LegoBrick] = []
    tracked_disappeared = {}  # we hold confirmed bricks marked for removal after some ticks
    min_distance: int = None
    min_appeared: int = None
    max_disappeared: int = None

    def __init__(self, server_communicator, min_distance=MIN_DISTANCE,
                 min_appeared=MIN_APPEARED, max_disappeared=MAX_DISAPPEARED):
        self.server_communicator = server_communicator
        self.min_distance = min_distance
        self.min_appeared = min_appeared
        self.max_disappeared = max_disappeared

    def update(self, lego_bricks_candidates: typing.List[LegoBrick]) -> typing.List[LegoBrick]:

        # copy the confirmed bricks
        possible_removed_bricks = self.confirmed_bricks.copy()

        # iterate through all candidates
        for candidate in lego_bricks_candidates:

            # remove the candidate from the possible removed bricks
            if candidate in possible_removed_bricks:
                possible_removed_bricks.remove(candidate)

            # check if this candidate is already in the list
            if candidate not in self.confirmed_bricks:

                # check if candidate is in minimum distance to any of confirmed bricks
                neighbour_brick = self.check_min_distance(candidate, self.confirmed_bricks)
                if not neighbour_brick:

                    # create or add a tick if it's not yet confirmed
                    if candidate in self.tracked_candidates:
                        self.tracked_candidates[candidate] += 1
                    else:
                        self.tracked_candidates[candidate] = 0

                else:
                    self.tracked_candidates[neighbour_brick] += 1
            else:
                # if the brick reappeared stop tracking it as disappeared
                if candidate in self.tracked_disappeared:
                    del self.tracked_disappeared[candidate]

        # start tracking the not reappeared bricks as possible removed
        for possible_removed_brick in possible_removed_bricks:

            if possible_removed_brick in self.tracked_disappeared:
                self.tracked_disappeared[possible_removed_brick] += 1
            else:
                self.tracked_disappeared[possible_removed_brick] = 0

        # we temporarily save disappeared
        # elements to delete them from dicts
        bricks_to_remove = []

        # remove the disappeared elements
        for brick, amount in self.tracked_disappeared.items():

            # check for the threshold value
            if amount > self.max_disappeared:

                # remember disappeared elements to delete them from dicts
                bricks_to_remove.append(brick)

                # remove the disappeared elements from the confirmed list
                self.confirmed_bricks.remove(brick)

                # if the brick is associated with an asset also send a remove request to the server
                if brick.status == LegoStatus.EXTERNAL_BRICK:
                    self.server_communicator.remove_lego_instance(brick)

        # remove the disappeared elements from dicts
        for brick in bricks_to_remove:

            del self.tracked_candidates[brick]
            del self.tracked_disappeared[brick]

        # add the qualified candidates to the confirmed list
        for candidate, amount in self.tracked_candidates.items():

            # check for the threshold value of new candidates
            if amount > self.min_appeared and candidate not in self.confirmed_bricks:
                # FIXME: add here a hook for the detection of the status INTERNAL or EXTERNAL
                candidate.status = LegoStatus.EXTERNAL_BRICK  # FIXME: remove as soon as hook is available
                self.confirmed_bricks.append(candidate)
                # if the brick is associated with an asset also send a create request to the server
                if candidate.status == LegoStatus.EXTERNAL_BRICK:
                    self.server_communicator.create_lego_instance(candidate)

        # finally return the updated list of confirmed bricks

        return self.confirmed_bricks

    # Check if the lego brick lay within min distance to the any in the list
    def check_min_distance(self, brick, bricks_list):

        neighbour_brick = None

        # Look for lego brick within min distance
        for potential_neighbour in bricks_list:

            # Compute distance in both dimensions
            distance_x = abs(potential_neighbour.centroid_x - brick.centroid_x)
            distance_y = abs(potential_neighbour.centroid_y - brick.centroid_y)

            # If distances are smaller than min the neighbour brick is found
            if (distance_x <= self.min_distance) & (distance_y <= self.min_distance):
                neighbour_brick = potential_neighbour

                # Return the found neighbour brick
                return neighbour_brick

        # Return None, no neighbour brick found
        return neighbour_brick
