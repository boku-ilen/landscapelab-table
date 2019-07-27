import logging
import typing
from LegoBricks import LegoBrick, LegoStatus
from LegoUI.UIElements.UIElement import UIElement

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

    def __init__(self, config, server_communicator, ui_root: UIElement, min_distance=MIN_DISTANCE,
                 min_appeared=MIN_APPEARED, max_disappeared=MAX_DISAPPEARED):
        self.config = config
        self.server_communicator = server_communicator
        self.ui_root = ui_root
        self.min_distance = min_distance
        self.min_appeared = min_appeared
        self.max_disappeared = max_disappeared

        # Initialize a flag for
        # changes in the map extent
        self.extend_changed = False

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

        # do ui update for all already confirmed bricks and mark as outdated if necessary
        for brick in self.confirmed_bricks:

            # mark all bricks as outdated that previously were on ui and now lie on the map or vice versa
            # this might happen when a ui elements visibility gets toggled
            if self.ui_root.brick_on_element(brick):
                if brick.status == LegoStatus.EXTERNAL_BRICK:
                    brick.status = LegoStatus.OUTDATED_BRICK
                    self.server_communicator.remove_lego_instance(brick)
            else:
                if brick.status == LegoStatus.INTERNAL_BRICK:
                    brick.status = LegoStatus.OUTDATED_BRICK

            # if the extend changed, set external bricks as outdated
            self.extend_changed = self.config.get("map_settings", "extend_changed")
            if self.extend_changed is True and brick.status == LegoStatus.EXTERNAL_BRICK:

                # change status of lego bricks to outdated
                brick.status = LegoStatus.OUTDATED_BRICK

                # set the flag back
                self.config.set("map_settings", "extend_changed", "False")

        # add the qualified candidates to the confirmed list and do ui update for them
        for candidate, amount in self.tracked_candidates.items():

            # check for the threshold value of new candidates
            if amount > self.min_appeared and candidate not in self.confirmed_bricks:

                if self.ui_root.brick_on_element(candidate):
                    candidate.status = LegoStatus.INTERNAL_BRICK
                else:
                    candidate.status = LegoStatus.EXTERNAL_BRICK

                # add a new lego brick to the confirmed lego bricks list
                self.confirmed_bricks.append(candidate)

                # if the brick is associated with an asset also send a create request to the server
                if candidate.status == LegoStatus.EXTERNAL_BRICK:
                    self.server_communicator.create_lego_instance(candidate)

        # handle mouse placed bricks and
        # do ui tick so that the button release event can be recognized and triggered
        self.ui_root.handle_mouse_bricks()
        self.ui_root.ui_tick()

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
