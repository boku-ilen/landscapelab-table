import logging
from typing import List

from LabTable.Model.Brick import Brick, BrickStatus, BrickShape, BrickColor, Token
from LabTable.Model.ProgramStage import ProgramStage
from LabTable.ExtentTracker import ExtentTracker
from LabTable.Model.Extent import Extent
from LabTable.BrickHandling.BrickHandler import BrickHandler

# configure logging
logger = logging.getLogger(__name__)


class Tracker:

    BRICKS_REFRESHED = False

    tracked_candidates = {}  # we hold candidates which are not confirmed yet for some ticks
    confirmed_bricks: List[Brick] = []
    virtual_bricks: List[Brick] = []
    tracked_disappeared = {}  # we hold confirmed bricks marked for removal after some ticks
    min_distance: int = None
    external_min_appeared: int = None
    external_max_disappeared: int = None
    brick_handler: BrickHandler = None
    next_brick_id: int = 0

    def __init__(self, config, brick_handler):

        self.config = config
        self.extent_tracker = ExtentTracker.get_instance()

        # get ticker thresholds from config
        self.min_distance = config.get("tracker_thresholds", "min_distance")
        self.external_min_appeared = config.get("tracker_thresholds", "external_min_appeared")
        self.external_max_disappeared = config.get("tracker_thresholds", "external_max_disappeared")
        self.internal_min_appeared = config.get("tracker_thresholds", "internal_min_appeared")
        self.internal_max_disappeared = config.get("tracker_thresholds", "internal_max_disappeared")

        self.brick_handler = brick_handler

        # we initialize it with all available configurations
        # as soon as an external game mode is choosen it should change accordingly
        # FIXME: this should maybe move in a change_gamemode()
        self.allowed_tokens: List[Token] = []
        brick_colors = config.get("brick_colors")
        for color in brick_colors:
            for shape in BrickShape:
                token = Token(shape, BrickColor[color])
                self.allowed_tokens.append(token)

        # Initialize a flag for changes in the map extent
        self.extent_changed = False
    
    def handle_new_brick(self, brick):
        brick.object_id = self.next_brick_id
        self.next_brick_id += 1

        brick.relative_position = self.extent_tracker.board \
            .get_position_within_extent(brick.centroid_x, brick.centroid_y)

        self.brick_handler.handle_new_brick(brick)

    def handle_removed_brick(self, brick):
        self.brick_handler.handle_removed_brick(brick)

    # re-initialize the tracker after the game mode changed
    def change_game_mode(self, allowed_tokens: List[Token]):
        self.allowed_tokens = allowed_tokens
        logger.info("the following tokens are allowed:")
        for token in self.allowed_tokens:
            logger.info("{}".format(token))
        self.tracked_disappeared.clear()
        self.virtual_bricks.clear()
        self.confirmed_bricks.clear()
        self.tracked_candidates.clear()

    # for externally remove tracked bricks
    def remove_external_brick(self, object_id):
        for brick in self.virtual_bricks:
            if brick.object_id == object_id:
                self.virtual_bricks.remove(brick)

    # for externally add a tracked brick
    def add_external_brick(self, brick: Brick):
        # TODO: maybe add security checks to not add the same brick twice etc?
        Extent.calc_local_pos(brick, self.extent_tracker.board, self.extent_tracker.map_extent)
        self.virtual_bricks.append(brick)

    # called once a frame while in ProgramStage EVALUATION or PLANNING
    # keeps track of bricks and returns a list of all currently confirmed bricks
    def update(self, brick_candidates: List[Brick], program_stage: ProgramStage):

        # count frames certain bricks have been continuously visible / gone
        self.do_brick_ticks(brick_candidates)

        # remove all bricks that have been gone for too long
        self.remove_overtime_disappeared_bricks()

        # do ui update for all confirmed bricks
        self.do_confirmed_ui_update()

        # remove bricks that are not virtual anymore
        self.remove_old_virtual_bricks()

        self.select_and_classify_candidates(program_stage)

        self.mark_external_bricks_outdated_if_map_updated()

        # finally, return the updated list of confirmed bricks
        return self.confirmed_bricks

    # iterates over all candidates and manages their tick counters
    def do_brick_ticks(self, brick_candidates: List[Brick]):

        # copy the confirmed bricks
        possible_removed_bricks = self.confirmed_bricks.copy()

        # iterate through all candidates
        for candidate in brick_candidates:

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
            if brick.status == BrickStatus.INTERNAL_BRICK:
                target_disappeared = self.internal_max_disappeared

            # check for the threshold value
            if amount > target_disappeared:

                # remember disappeared elements to delete them from dicts
                bricks_to_remove.append(brick)

                # remove the disappeared elements from the confirmed list
                self.confirmed_bricks.remove(brick)
                Tracker.BRICKS_REFRESHED = True

                # if the brick is associated with an object also send a remove request to the server
                if brick.status == BrickStatus.EXTERNAL_BRICK:
                    self.handle_removed_brick(brick)

        # remove the disappeared elements from dicts
        for brick in bricks_to_remove:
            del self.tracked_candidates[brick]
            del self.tracked_disappeared[brick]

    # does ui update for all already confirmed bricks and mark as outdated if necessary
    def do_confirmed_ui_update(self):

        for brick in self.confirmed_bricks:

            # mark all bricks as outdated that previously were on ui and now lie on the map or vice versa
            # this might happen when a ui elements visibility gets toggled
            if brick.status == BrickStatus.INTERNAL_BRICK:
                Tracker.set_brick_outdated(brick)

    def remove_old_virtual_bricks(self):

        # update virtual bricks
        for v_brick in self.virtual_bricks:

            # remove any virtual internal bricks that do not lie on ui elements anymore
            if v_brick.status == BrickStatus.INTERNAL_BRICK:
                self.virtual_bricks.remove(v_brick)

    # selects those candidates that appeared long enough to be considered confirmed and add them to the confirmed list
    # also does ui update for those bricks and classifies them
    def select_and_classify_candidates(self, program_stage):

        # add the qualified candidates to the confirmed list and do ui update for them
        for candidate, amount in self.tracked_candidates.items():

            # select the correct threshold on whether or not the candidate would be internal
            # (internal bricks appear faster)
            target_appeared = self.external_min_appeared

            # check for the threshold value of new candidates
            if amount > target_appeared and candidate not in self.confirmed_bricks:

                # if the brick is on top of a virtual brick, remove it and mark the brick as outdated
                virtual_brick = self.check_min_distance(candidate, self.virtual_bricks)
                if virtual_brick:
                    pass
                    self.remove_external_virtual_brick(virtual_brick)
                    candidate.status = BrickStatus.OUTDATED_BRICK

                else:
                    if self.check_brick_valid(candidate):
                        candidate.status = BrickStatus.EXTERNAL_BRICK
                        # if the brick is associated with an object also send a create request to the server
                        self.handle_new_brick(candidate)
                    else:
                        candidate.status = BrickStatus.OUTDATED_BRICK

                # add a new brick to the confirmed bricks list
                self.confirmed_bricks.append(candidate)

                Tracker.BRICKS_REFRESHED = True

        # loop through all virtual candidates (= all mouse placed bricks on first frame) and set correct status
        for brick in filter(lambda b: b.status == BrickStatus.CANDIDATE_BRICK, self.virtual_bricks):
            Tracker.BRICKS_REFRESHED = True

            logger.debug("classifying mouse brick {}".format(brick))

            brick.status = BrickStatus.EXTERNAL_BRICK
            self.handle_new_brick(brick)

    # Check if the brick lies within min distance to the any in the list, returns None if no neighbour was found
    def check_min_distance(self, brick: Brick, bricks_list) -> [None, Brick]:

        neighbour_brick = None

        # Look for brick within min distance
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

            logger.debug("recalculate virtual brick position")
            for brick in self.virtual_bricks:
                if brick.status == BrickStatus.EXTERNAL_BRICK:
                    Extent.calc_local_pos(brick, self.extent_tracker.board, self.extent_tracker.map_extent)

            logger.info("set bricks outdated because extent changed")
            self.invalidate_external_bricks()

            # set the flag back
            self.extent_tracker.extent_changed = False

    @staticmethod
    def set_brick_outdated(brick: Brick):

        brick.status = BrickStatus.OUTDATED_BRICK
        Tracker.BRICKS_REFRESHED = True

    def set_virtual_brick_at_global_pos_of(self, brick: Brick):

        virtual_brick = brick.clone()
        Extent.calc_local_pos(virtual_brick, self.extent_tracker.board, self.extent_tracker.map_extent)

        self.virtual_bricks.append(virtual_brick)
        Tracker.BRICKS_REFRESHED = True

    def remove_external_virtual_brick(self, brick: Brick):

        self.handle_removed_brick(brick)
        self.virtual_bricks.remove(brick)

    # sets all external bricks to outdated
    def invalidate_external_bricks(self):

        return

        for brick in self.confirmed_bricks:
            if brick.status == BrickStatus.EXTERNAL_BRICK:
                # change status of bricks to outdated
                self.set_virtual_brick_at_global_pos_of(brick)
                Tracker.set_brick_outdated(brick)

    # checks if the brick is allowed in the current program stage
    def check_brick_valid(self, brick: Brick):

        for token in self.allowed_tokens:
            if token == brick.token:
                logger.debug("allowed brick: {}".format(brick))
                return True

        logger.warning("invalid brick: {} (allowed: {})".format(brick.token, [str(token) for token in self.allowed_tokens]))
        return False
