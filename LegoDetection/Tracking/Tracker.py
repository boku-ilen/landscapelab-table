import logging
import typing
from Tracking.LegoBrick import LegoBrick

# configure logging
logger = logging.getLogger(__name__)

MIN_DISTANCE = 6
MAX_DISAPPEARED = 20


class Tracker:

    server_communicator = None
    tracked_candidates = {}  # we hold candidates which are not confirmed yet for some ticks
    confirmed_bricks: typing.List[LegoBrick] = []
    tracked_disappeared = {}  # we hold confirmed bricks marked for removal after some ticks
    min_distance: int = None
    max_disappeared: int = None

    def __init__(self, server_communicator, min_distance=MIN_DISTANCE, max_disappeared=MAX_DISAPPEARED):
        self.server_communicator = server_communicator
        self.min_distance = min_distance
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
                # create or add a tick if it's not yet confirmed
                if candidate in self.tracked_candidates:
                    self.tracked_candidates[candidate] += 1
                else:
                    self.tracked_candidates[candidate] = 0
            else:
                # if the brick reappeared stop tracking it
                if candidate in self.tracked_disappeared:
                    del self.tracked_disappeared[candidate]

        # start tracking the not reappeared bricks as possible removed
        for possible_removed_brick in possible_removed_bricks:
            if possible_removed_brick in self.tracked_disappeared:
                self.tracked_disappeared[possible_removed_brick] += 1
            else:
                self.tracked_disappeared[possible_removed_brick] = 0

        # remove the disappeared elements from the confirmed list
        for brick, amount in self.tracked_disappeared.items():
            # check for the threshold value
            if amount > self.max_disappeared:
                self.confirmed_bricks.remove(brick)
                # if the brick is associated with an asset also send a remove request to the server
                if brick.status == LegoBrick.status.EXTERNAL_BRICK:
                    self.server_communicator.remove_lego_instance(brick)

        # add the qualified candidates to the confirmed list
        for candidate, amount in self.tracked_candidates.items():
            # check for the threshold value
            if amount > self.max_disappeared:  # FIXME: other name or different variable
                # FIXME: add here a hook for the detection of the status INTERNAL or EXTERNAL
                candidate.status = LegoBrick.status.EXTERNAL_BRICK  # FIXME: remove as soon as hook is available
                self.confirmed_bricks.append(candidate)
                # if the brick is associated with an asset also send a create request to the server
                if candidate.status == LegoBrick.status.EXTERNAL_BRICK:
                    self.server_communicator.create_lego_instance(candidate)

        # finally return the updated list of confirmed bricks
        return self.confirmed_bricks
