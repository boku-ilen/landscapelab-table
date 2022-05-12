import logging
import socket

from Configurator import Configurator
from LabTable.Communication.Communicator import Communicator
from LabTable.Model.Brick import Brick, BrickStatus, BrickShape
from LabTable.Model.Extent import Extent
from LabTable.ExtentTracker import ExtentTracker


# Configure logging
from Model.Score import Score
from TableUI.UIElements import UISetup
from TableUI.UIElements.ProgressBar import ProgressBar
from TableUI.UIElements.UIElement import UIElement

logger = logging.getLogger(__name__)

# remote communication protocol from/to the LL
SEND_REC_CREATE_OBJECT_MSG = {
    "keyword": "NEW_TOKEN",
    "position_x": 0.0,
    "position_y": 0.0,
    "shape": "",
    "color": "",
    "object_id": 0,  # optional: only sent by LL (REC)
    "data": []  # optional for later (provide additional information)
}
SEND_REC_UPDATE_OBJECT_MSG = {
    "keyword": "SET_TOKEN_POSITION",
    "object_id": 0,
    "position_x": 0.0,
    "position_y": 0.0
}
SEND_REC_REMOVE_OBJECT_MSG = {
    "keyword": "REMOVE_TOKEN",
    "object_id": 0
}
REC_OBJECT_ANSWER_MSG = {  # Answer to create, update, remove
    "keyword": "TOKEN_ANSWER",
    "placement_allowed": False,  # in case of create or update
    "object_id": 0,
    "data": []  # optional for later (provide additional information)
}
SEND_HANDSHAKE_MSG = {
    "keyword": "TABLE_HANDSHAKE",
    "hostname": "",  # TODO: maybe provide other configuration too
    "provided_tokens": []  # array of token (see above) [{ "shape": .., "color": ...}, ...]
}
REC_GAMESTATE_INFO_MSG = {  # Received after the first handshake and if the gamestate changes
    "keyword": "GAMESTATE_INFO",
    "used_tokens": [{
        "shape": "",
        "color": "",
        "icon_svg": "",  # the svg as ascii string
        "disappear_after_seconds": 0.0
    }],
    "scores": [{
        "score_id": 0,
        "name": None,  # optional caption
        "initial_value": 0.0,
        "target_value": 0.0
    }],
    "existing_tokens": [{
        "object_id": 0,
        "position_x": 0.0,
        "position_y": 0.0,
        "shape": "",
        "color": "",
        "data": []  # optional
    }],
    "start_position_x": 0.0,
    "start_position_y": 0.0,
    "start_extent_x": 0.0,  # height
    "start_extent_y": 0.0,  # width
    "projection_epsg": 0  # EPSG Code (optional, default is Austria Lambert)
}
REC_UPDATE_SCORE_MSG = {
    "keyword": "SCORE_UPDATE",
    "score_id": 0,
    "value": 0.0  # FIXME: is this an absolute value or do we add/subtract from the existing value?
}
SEND_SET_EXTENT_MSG = {  # this is sent on change to the LL
    "keyword": "TABLE_EXTENT",
    "min_x": 0.0,
    "min_y": 0.0,
    "max_x": 0.0,
    "max_y": 0.0
}
REC_PLAYER_POSITION_MSG = {  # this is received on change from LL
    "keyword": "PLAYER_POS",
    "projected_x": 0.0,
    "projected_y": 0.0
}


# the LL specific implementation part for the communication
class LLCommunicator(Communicator):

    tracker = None
    progressbars_ui: UIElement = None

    def __init__(self, config: Configurator):

        # call super()
        self.ip = config.get("landscapelab", "ip")
        self.port = config.get("landscapelab", "port")
        super().__init__(config)

        self.extent_tracker = ExtentTracker.get_instance()

        # set the callback functions for the received messages from the LL
        self.keyword_callbacks = {
            SEND_REC_CREATE_OBJECT_MSG["keyword"]: self.create_local_brick,
            SEND_REC_UPDATE_OBJECT_MSG["keyword"]: self.update_local_brick,
            SEND_REC_REMOVE_OBJECT_MSG["keyword"]: self.remove_local_brick,
            REC_GAMESTATE_INFO_MSG["keyword"]: self.game_mode_change,
            REC_UPDATE_SCORE_MSG["keyword"]: self.update_local_score,
            REC_PLAYER_POSITION_MSG["keyword"]: self.update_player_position
        }

        self.provided_tokens = []
        for color in config.get("brick_colors"):
            for shape in BrickShape:
                if shape.value > 0:
                    self.provided_tokens.append({"color": color, "shape": shape.name})

    def on_open(self, ws):
        super().on_open(ws)
        self.initialize_handshake()

    # get the initial configuration settings related to the LabTable from the LL
    def initialize_handshake(self):

        # store the settings we later got as answer in our configuration
        def handshake_callback(response: dict):
            self.game_mode_change(response)

        message = SEND_HANDSHAKE_MSG.copy()
        message["hostname"] = socket.gethostname()
        message["provided_tokens"] = self.provided_tokens

        self.send_message(message, handshake_callback)

    # Create remote brick instance
    def create_remote_brick_instance(self, brick: Brick):

        def create_callback(response: dict):

            if "placement_allowed" in response:
                if response["placement_allowed"]:

                    # set the remote asset id
                    brick.object_id = response["id"]

                else:
                    logger.debug("could not remotely create brick {}".format(brick))
                    brick.status = BrickStatus.OUTDATED_BRICK

            else:
                logger.warning("protocol error which creating brick {}".format(brick))
                # TODO: should the brick status change?

        logger.debug("creating a brick instance for {}".format(brick))

        # Compute geographical coordinates for bricks
        Extent.calc_world_pos(brick, self.extent_tracker.board, self.extent_tracker.map_extent)

        # Send request creating remote brick instance and save the response
        message = SEND_REC_CREATE_OBJECT_MSG.copy()
        # TODO: send the brick type
        message["position"] = [brick.map_pos_x, brick.map_pos_y]

        self.send_message(message, create_callback)

    # Remove remote brick instance
    def remove_remote_brick_instance(self, brick_instance: Brick):

        def remove_callback(response: dict):
            pass
            # TODO: the LL might want to prevent to delete a brick

        message = SEND_REC_REMOVE_OBJECT_MSG.copy()
        message["object_id"] = brick_instance.object_id

        # Send a request to remove brick instance
        self.send_message(message, remove_callback)

    # initiates corner point update of the given main map extent and informs the LandscapeLab
    def update_extent_info(self, extent: Extent):

        def extent_callback(response: dict):
            # TODO: we might want to validate if the target successfully accepted the extent change
            pass

        message = SEND_SET_EXTENT_MSG.copy()
        message["min_x"] = extent.x_min
        message["min_y"] = extent.y_min
        message["max_x"] = extent.x_max
        message["max_y"] = extent.y_max

        self.send_message(message, extent_callback)

    # update the player position on the display where the landscapelab player(s) are positioned
    def update_player_position(self, message_id, message: dict):
        pass

    def game_mode_change(self, message_id, response: dict):

        epsg = response["projection_epsg"]
        start_position = (response["start_position_x"], response["start_position_y"])
        # FIXME: we might have to recalculate this to a zoomlevel
        start_extent = (response["start_extent_x"], response["start_extent_y"])

        # TODO: setup the new map

        # FIXME: set the used token types in tracker (not yet implemented)

        # add new tokens
        # FIXME: we do need to delete the old ones from the tracker?
        for token in response["existing_tokens"]:
            self.create_local_brick(message_id, token)

        # create the scores for the new game mode
        scores = []
        for score_dict in response["scores"]:
            identifier = score_dict["identifier"]
            initial_value = score_dict["initial_value"]
            target_value = score_dict["target_value"]
            name = ""
            if score_dict["name"]:
                name = score_dict["name"]
            score = Score(identifier, target_value, initial_value, name)
            scores.append(score)

        UISetup.add_progressbars_to_ui(self.progressbars_ui, self.config, scores)

        # FIXME: set the game mode to EXTERNAL and do not accept remote inputs while INTERNAL

    def create_local_brick(self, message_id, response: dict):

        shape = response["shape"]
        color = response["color"]
        new_brick = Brick(0, 0, shape, color)  # centroid will be calculated later
        new_brick.status = BrickStatus.EXTERNAL_BRICK
        new_brick.object_id = response["object_id"]
        new_brick.map_pos_x = response["position_x"]
        new_brick.map_pos_y = response["position_y"]

        # TODO: move this to the tracker?
        Extent.calc_local_pos(new_brick, self.extent_tracker.board, self.extent_tracker.map_extent)
        self.tracker.add_external_brick(new_brick)

    # FIXME: this is not used yet anyhow
    def update_local_brick(self, message_id, response: dict):
        pass

    def remove_local_brick(self, message_id, response: dict):
        object_id = response["object_id"]
        self.tracker.remove_external_brick(object_id)

    def update_local_score(self, message_id, response: dict):

        score_id = response["score_id"]
        value = response["value"]

        # FIXME: this logic should move somewhere where the UI is managed
        for progress_bar in self.progressbars_ui.get_by_type(ProgressBar):
            if progress_bar.score:
                if progress_bar.score.identifier == score_id:
                    progress_bar.score.set_value(value)
