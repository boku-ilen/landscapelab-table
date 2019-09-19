import logging
from typing import Callable, List

from ..LegoBricks import LegoBrick, LegoStatus
from ..LegoUI.UIElements.UIElement import UIElement
from ..ExtentTracker import ExtentTracker
from ..LegoExtent import LegoExtent

# configure logging
logger = logging.getLogger(__name__)

PLAYER_POSITION_ASSET_ID = 13


class Tracker:

    BRICKS_REFRESHED = False

    server_communicator = None
    tracked_candidates = {}  # we hold candidates which are not confirmed yet for some ticks
    confirmed_bricks: List[LegoBrick] = []
    virtual_bricks: List[LegoBrick] = []
    tracked_disappeared = {}  # we hold confirmed bricks marked for removal after some ticks
    min_distance: int = None
    external_min_appeared: int = None
    external_max_disappeared: int = None

    def __init__(self, config, board, server_communicator, ui_root: UIElement):
        self.config = config
        self.extent_tracker = ExtentTracker.get_instance()
        self.server_communicator = server_communicator
        self.ui_root = ui_root

        # get ticker thresholds from config
        self.min_distance = config.get("tracker-thresholds", "min-distance")
        self.external_min_appeared = config.get("tracker-thresholds", "external-min-appeared")
        self.external_max_disappeared = config.get("tracker-thresholds", "external-max-disappeared")
        self.internal_min_appeared = config.get("tracker-thresholds", "internal-min-appeared")
        self.internal_max_disappeared = config.get("tracker-thresholds", "internal-max-disappeared")

        # Initialize a flag for
        # changes in the map extent
        self.extent_changed = False

        # Initialize the current player
        self.player = None

    # syncs all currently known bricks with the currently known bricks list on the server
    def sync_with_server_side_bricks(self):

        # get server side bricks
        asset_ids = self.config.get("stored_instances", "asset_ids")
        server_bricks = []
        for asset_id in asset_ids:
            server_bricks += self.server_communicator.get_stored_lego_instances(asset_id)

        # handle bricks
        if server_bricks is not None:

            # get list of all currently known brick IDs
            v_brick_ids = [b.asset_id for b in self.virtual_bricks]
            c_brick_ids = [b.asset_id for b in self.confirmed_bricks]
            s_brick_ids = [b.asset_id for b in server_bricks]

            for brick in server_bricks:

                # set the current player
                if brick.asset_id == PLAYER_POSITION_ASSET_ID and brick != self.player:
                    self.player = brick
                    self.set_virtual_brick_at_global_pos_of(self.player)
                    logger.debug("set the player {}".format(self.player))

                # add server brick to virtual bricks if it's ID is unknown
                elif brick.asset_id not in v_brick_ids \
                        and brick.asset_id not in c_brick_ids:
                    self.virtual_bricks.append(brick)

            for v_brick in self.virtual_bricks:

                # remove all virtual bricks that have been removed externally
                if v_brick.status == LegoStatus.EXTERNAL_BRICK and v_brick.asset_id not in s_brick_ids \
                        and v_brick.asset_id != PLAYER_POSITION_ASSET_ID:
                    self.virtual_bricks.remove(v_brick)
                    logger.info("removed externally removed virtual brick")

            # TODO BELOW IS AN OPTIONAL FEATURE THAT REINTRODUCES CONFIRMED BRICKS WHICH HAVE BEEN FALSELY REMOVED FROM
            #  THE SERVER. FROM MY TESTING IT SEEMS LIKE IT DOES NOT EXACTLY DO WHAT IT IS SUPPOSED TO DO.
            #  (probably because the fetched brick list does not include special bricks like the player teleport brick)
            #  IT NEEDS FURTHER TESTING AND I DEEM IT TOO RISKY AND INSIGNIFICANT TO BE INCLUDED IN THE WORKSHOPS
            # re-register all confirmed bricks that have disappeared from the server list
            """
            for c_brick in self.confirmed_bricks:
                if c_brick.status == LegoStatus.EXTERNAL_BRICK and c_brick.asset_id not in s_brick_ids:
                    self.server_communicator.create_lego_instance(c_brick)
                    logger.info("re-registered missing brick in server: {}".format(c_brick))
            """

    # called once a frame while in ProgramStage EVALUATION or LEGO_DETECTION
    # keeps track of bricks and returns a list of all currently confirmed bricks
    def update(self, lego_bricks_candidates: List[LegoBrick]):

        # count frames certain bricks have been continuously visible / gone
        self.do_brick_ticks(lego_bricks_candidates)

        # remove all bricks that have been gone for too long
        self.remove_overtime_disappeared_bricks()

        # do ui update for all confirmed bricks
        self.do_confirmed_ui_update()

        # remove bricks that are not virtual anymore, e.g. the player
        self.remove_old_virtual_bricks()

        self.select_and_classify_candidates()

        # handle mouse placed bricks and
        # do ui tick so that the button release event can be recognized and triggered
        self.ui_root.ui_tick()

        self.mark_external_bricks_outdated_if_map_updated()

        # finally return the updated list of confirmed bricks
        return self.confirmed_bricks

    # iterates over all candidates and manages their tick counters
    def do_brick_ticks(self, lego_bricks_candidates: List[LegoBrick]):
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

    # removes those bricks that have been invisible for too long
    def remove_overtime_disappeared_bricks(self):

        # we temporarily save disappeared
        # elements to delete them from dicts
        bricks_to_remove = []

        # remove the disappeared elements
        for brick, amount in self.tracked_disappeared.items():

            # select correct threshold on whether the brick is internal or not
            # (internal bricks disappear faster)
            target_disappeared = self.external_max_disappeared
            if brick.status == LegoStatus.INTERNAL_BRICK:
                target_disappeared = self.internal_max_disappeared

            # check for the threshold value
            if amount > target_disappeared:

                # remember disappeared elements to delete them from dicts
                bricks_to_remove.append(brick)

                # remove the disappeared elements from the confirmed list
                self.confirmed_bricks.remove(brick)
                Tracker.BRICKS_REFRESHED = True

                # if the brick is associated with an asset also send a remove request to the server
                if brick.status == LegoStatus.EXTERNAL_BRICK:
                    self.server_communicator.remove_lego_instance(brick)

        # remove the disappeared elements from dicts
        for brick in bricks_to_remove:
            del self.tracked_candidates[brick]
            del self.tracked_disappeared[brick]

    # does ui update for all already confirmed bricks and mark as outdated if necessary
    def do_confirmed_ui_update(self):

        for brick in self.confirmed_bricks:

            # mark all bricks as outdated that previously were on ui and now lie on the map or vice versa
            # this might happen when a ui elements visibility gets toggled
            if self.brick_on_ui(brick):
                if brick.status == LegoStatus.EXTERNAL_BRICK:
                    Tracker.set_brick_outdated(brick)
                    self.server_communicator.remove_lego_instance(brick)
            else:
                if brick.status == LegoStatus.INTERNAL_BRICK:
                    Tracker.set_brick_outdated(brick)

    def remove_old_virtual_bricks(self):

        # update virtual bricks
        for v_brick in self.virtual_bricks:

            # remove any virtual internal bricks that do not lie on ui elements anymore
            if v_brick.status == LegoStatus.INTERNAL_BRICK and not self.brick_on_ui(v_brick):
                self.virtual_bricks.remove(v_brick)

            # remove all previous players
            elif v_brick.asset_id == PLAYER_POSITION_ASSET_ID and v_brick != self.player:
                self.remove_external_virtual_brick(v_brick)
                logger.debug("removed previous players {}".format(v_brick))

    # selects those candidates that appeared long enough to be considered confirmed and add them to the confirmed list
    # also does ui update for those bricks and classifies them
    def select_and_classify_candidates(self):
        # add the qualified candidates to the confirmed list and do ui update for them
        for candidate, amount in self.tracked_candidates.items():

            # select the correct threshold on whether or not the candidate would be internal
            # (internal bricks appear faster)
            target_appeared = self.external_min_appeared
            if self.brick_would_land_on_ui(candidate):
                target_appeared = self.internal_min_appeared
            # NOTE calling brick_would_land_on_ui every frame might cause performance hits
            #  a cheaper solution would be to call it once the first frame the candidate registered and save the result

            # check for the threshold value of new candidates
            if amount > target_appeared and candidate not in self.confirmed_bricks:

                # if the brick is on top of a virtual brick, remove it and mark the brick as outdated
                virtual_brick = self.check_min_distance(candidate, self.virtual_bricks)
                if virtual_brick and virtual_brick.asset_id != PLAYER_POSITION_ASSET_ID:
                    self.remove_external_virtual_brick(virtual_brick)
                    candidate.status = LegoStatus.OUTDATED_BRICK

                else:
                    if self.brick_on_ui(candidate):
                        candidate.status = LegoStatus.INTERNAL_BRICK
                    else:
                        candidate.status = LegoStatus.EXTERNAL_BRICK
                        # if the brick is associated with an asset also send a create request to the server
                        self.server_communicator.create_lego_instance(candidate)

                # add a new lego brick to the confirmed lego bricks list
                self.confirmed_bricks.append(candidate)

                Tracker.BRICKS_REFRESHED = True

        # loop through all virtual candidates (= all mouse placed bricks on first frame) and set correct status
        for brick in filter(lambda b: b.status == LegoStatus.CANDIDATE_BRICK, self.virtual_bricks):
            Tracker.BRICKS_REFRESHED = True

            logger.info("classifying mouse brick")

            if self.brick_on_ui(brick):
                brick.status = LegoStatus.INTERNAL_BRICK
            else:
                brick.status = LegoStatus.EXTERNAL_BRICK
                self.server_communicator.create_lego_instance(brick)

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

    # marks external bricks as outdated if the map was updated
    def mark_external_bricks_outdated_if_map_updated(self):
        # if the extent changed, set external bricks as outdated
        self.extent_changed = self.extent_tracker.extent_changed
        if self.extent_changed is True:

            logger.info("recalculate virtual brick position")
            for brick in self.virtual_bricks:
                if brick.status == LegoStatus.EXTERNAL_BRICK:
                    LegoExtent.calc_local_pos(brick, self.extent_tracker.board, self.extent_tracker.map_extent)

            logger.info("set bricks outdated because extent changed")
            for brick in self.confirmed_bricks:
                if brick.status == LegoStatus.EXTERNAL_BRICK:
                    # change status of lego bricks to outdated
                    self.set_virtual_brick_at_global_pos_of(brick)
                    Tracker.set_brick_outdated(brick)

            # set the flag back
            self.extent_tracker.extent_changed = False

    @staticmethod
    def set_brick_outdated(brick: LegoBrick):
        brick.status = LegoStatus.OUTDATED_BRICK
        Tracker.BRICKS_REFRESHED = True

    def set_virtual_brick_at_global_pos_of(self, brick: LegoBrick):
        virtual_brick = brick.clone()
        LegoExtent.calc_local_pos(virtual_brick, self.extent_tracker.board, self.extent_tracker.map_extent)

        self.virtual_bricks.append(virtual_brick)
        Tracker.BRICKS_REFRESHED = True

    def remove_external_virtual_brick(self, brick: LegoBrick):
        self.server_communicator.remove_lego_instance(brick)
        self.virtual_bricks.remove(brick)

    def brick_on_ui(self, brick):
        brick_on_beamer = LegoExtent.remap(brick, self.extent_tracker.board, self.extent_tracker.beamer)
        return self.ui_root.brick_on_element(brick_on_beamer)

    def brick_would_land_on_ui(self, brick):
        brick_on_beamer = LegoExtent.remap(brick, self.extent_tracker.board, self.extent_tracker.beamer)
        return self.ui_root.brick_would_land_on_element(brick_on_beamer)
