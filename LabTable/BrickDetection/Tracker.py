import logging
from typing import List

from LabTable.Model.Brick import Brick, BrickStatus, BrickShape
from LabTable.TableUI.UIElements.UIElement import UIElement
from LabTable.Model.ProgramStage import ProgramStage
from LabTable.ExtentTracker import ExtentTracker
from LabTable.Model.Extent import Extent

# configure logging
logger = logging.getLogger(__name__)


class Tracker:

    BRICKS_REFRESHED = False

    landscape_lab = None
    tracked_candidates = {}  # we hold candidates which are not confirmed yet for some ticks
    confirmed_bricks: List[Brick] = []
    virtual_bricks: List[Brick] = []
    tracked_disappeared = {}  # we hold confirmed bricks marked for removal after some ticks
    min_distance: int = None
    external_min_appeared: int = None
    external_max_disappeared: int = None

    def __init__(self, config, ui_root: UIElement, ll_communicator):

        self.config = config
        self.extent_tracker = ExtentTracker.get_instance()
        self.landscape_lab = ll_communicator
        self.ui_root = ui_root

        # get ticker thresholds from config
        self.min_distance = config.get("tracker_thresholds", "min_distance")
        self.external_min_appeared = config.get(
            "tracker_thresholds", "external_min_appeared")
        self.external_max_disappeared = config.get(
            "tracker_thresholds", "external_max_disappeared")
        self.internal_min_appeared = config.get(
            "tracker_thresholds", "internal_min_appeared")
        self.internal_max_disappeared = config.get(
            "tracker_thresholds", "internal_max_disappeared")

        # we initialize it with all available configurations
        # as soon as an external game mode is choosen it should change accordingly
        # FIXME: this should maybe move in a change_gamemode()
        self.allowed_bricks = []
        brick_colors = config.get("brick_colors")
        for color in brick_colors:
            for shape in BrickShape:
                self.allowed_bricks.append((color, shape))

        # Initialize a flag for changes in the map extent
        self.extent_changed = False

    # for externally remove tracked bricks
    def remove_external_brick(self, object_id):
        for brick in self.virtual_bricks:
            if brick.object_id == object_id:
                self.virtual_bricks.remove(brick)

    # for externally add a tracked brick
    def add_external_brick(self, brick: Brick):
        # TODO: maybe add security checks to not add the same brick twice etc?
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

        # handle mouse placed bricks and
        # do ui tick so that the button release event can be recognized and triggered
        self.ui_root.ui_tick()

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
                    # FIXME: distinguish handler
                    self.landscape_lab.remove_remote_brick_instance(brick)

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
                if brick.status == BrickStatus.EXTERNAL_BRICK:
                    Tracker.set_brick_outdated(brick)
                    # FIXME: distinguish handler
                    self.landscape_lab.remove_remote_brick_instance(brick)
            else:
                if brick.status == BrickStatus.INTERNAL_BRICK:
                    Tracker.set_brick_outdated(brick)

    def remove_old_virtual_bricks(self):

        # update virtual bricks
        for v_brick in self.virtual_bricks:

            # remove any virtual internal bricks that do not lie on ui elements anymore
            if v_brick.status == BrickStatus.INTERNAL_BRICK and not self.brick_on_ui(v_brick):
                self.virtual_bricks.remove(v_brick)

    # selects those candidates that appeared long enough to be considered confirmed and add them to the confirmed list
    # also does ui update for those bricks and classifies them
    def select_and_classify_candidates(self, program_stage):

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
                if virtual_brick:
                    self.remove_external_virtual_brick(virtual_brick)
                    candidate.status = BrickStatus.OUTDATED_BRICK

                else:
                    if self.brick_on_ui(candidate):
                        candidate.status = BrickStatus.INTERNAL_BRICK
                    else:
                        if self.check_brick_valid(candidate):
                            candidate.status = BrickStatus.EXTERNAL_BRICK
                            # if the brick is associated with an object also send a create request to the server
                            # FIXME: distinguish action based on brick configuration (eg teleport)
                            self.landscape_lab.create_remote_brick_instance(candidate)
                        else:
                            candidate.status = BrickStatus.OUTDATED_BRICK

                # add a new brick to the confirmed bricks list
                self.confirmed_bricks.append(candidate)

                Tracker.BRICKS_REFRESHED = True

        # loop through all virtual candidates (= all mouse placed bricks on first frame) and set correct status
        for brick in filter(lambda b: b.status == BrickStatus.CANDIDATE_BRICK, self.virtual_bricks):
            Tracker.BRICKS_REFRESHED = True

            logger.debug("classifying mouse brick {}".format(brick))

            if self.brick_on_ui(brick):
                brick.status = BrickStatus.INTERNAL_BRICK
            else:
                brick.status = BrickStatus.EXTERNAL_BRICK
                # FIXME: distinguish action based on brick configuration (eg teleport)
                self.landscape_lab.create_remote_brick_instance(brick)

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

        # FIXME: distinguish action
        self.landscape_lab.remove_remote_brick_instance(brick)
        self.virtual_bricks.remove(brick)

    def brick_on_ui(self, brick):

        brick_on_beamer = Extent.remap_brick(brick, self.extent_tracker.board, self.extent_tracker.beamer)
        return self.ui_root.brick_on_element(brick_on_beamer)

    def brick_would_land_on_ui(self, brick):

        brick_on_beamer = Extent.remap_brick(brick, self.extent_tracker.board, self.extent_tracker.beamer)
        return self.ui_root.brick_would_land_on_element(brick_on_beamer)

    # sets all external bricks to outdated
    def invalidate_external_bricks(self):

        for brick in self.confirmed_bricks:
            if brick.status == BrickStatus.EXTERNAL_BRICK:
                # change status of bricks to outdated
                self.set_virtual_brick_at_global_pos_of(brick)
                Tracker.set_brick_outdated(brick)

    # checks if the brick is allowed in the current program stage
    def check_brick_valid(self, brick: Brick):

        brick_type = (brick.color, brick.shape)
        if brick_type in self.allowed_bricks:
            return True
        return False
