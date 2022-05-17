import logging
import socket

from LabTable.Configurator import Configurator
from LabTable.Communication.Communicator import Communicator
from LabTable.Model.Brick import Brick, BrickStatus, BrickShape, Token, BrickColor
from LabTable.Model.Extent import Extent
from LabTable.ExtentTracker import ExtentTracker

import LabTable.Model.Brick as brick_config

# Configure logging
from LabTable.Model.Score import Score
from LabTable.TableUI.UIElements import UISetup
from LabTable.TableUI.UIElements.ProgressBar import ProgressBar
from LabTable.TableUI.UIElements.UIElement import UIElement
from LabTable.Model.ProgramStage import CurrentProgramStage
from LabTable.Model.Vector import Vector
from LabTable.TableUI.MainMap import MainMap
from LabTable.TableUI.UIElements.MiniMap import MiniMap

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
        "icon_name": "",  # the icon identifier
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
    "minimap_min_x": 0.0,
    "minimap_min_y": 0.0,
    "minimap_max_x": 0.0,
    "minimap_max_y": 0.0,
    "projection_epsg": 0  # EPSG Code (optional, default is Austria Lambert)
}
REC_UPDATE_SCORE_MSG = {
    "keyword": "SCORE_UPDATE",
    "score_id": 0,
    "value": 0.0  # as new, absolute value
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
    main_map: MainMap = None
    mini_map: MiniMap = None

    def __init__(self, config: Configurator, program_stage: CurrentProgramStage):

        # call super()
        self.ip = config.get("landscapelab", "ip")
        self.port = config.get("landscapelab", "port")
        super().__init__(config)

        self.extent_tracker = ExtentTracker.get_instance()
        self.program_stage = program_stage

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
                    #FIXME: does this reference to the brick instance work?
                    brick.object_id = int(response["object_id"])

                else:
                    logger.info("placement of brick {} is not allowed".format(brick))
                    brick.status = BrickStatus.OUTDATED_BRICK

            else:
                logger.warning("protocol error which creating brick {}".format(brick))
                # TODO: should the brick status change?

        logger.debug("creating a brick instance for {}".format(brick))

        # Compute geographical coordinates for bricks
        Extent.calc_world_pos(brick, self.extent_tracker.board, self.extent_tracker.map_extent)

        # Send request creating remote brick instance and save the response
        message = SEND_REC_CREATE_OBJECT_MSG.copy()
        message["shape"] = str(brick.token.shape).replace("BrickShape.", "")
        message["color"] = str(brick.token.color).replace("BrickColor.", "")
        message["position_x"] = brick.map_pos_x
        message["position_y"] = brick.map_pos_y

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
    def update_player_position(self, message: dict):
        pass

    # this initializes a new game mode
    # dict of format: {
    #   'keyword': 'GAMESTATE_INFO',
    #   'used_tokens': [
    #       {   
    #           'shape': 'SQUARE_BRICK', 'color': 'RED_BRICK', 
    #           'icon_name': 'windmill_icon', 'disappear_after_seconds': 0
    #       }, ...
    #   ]
    #   'scores': [{...}], 
    #   'existing_tokens': [{...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}, {...}, ...],
    #   'start_position_x': 662000.125, 'start_position_y': 454750.09375, 
    #   'start_extent_x': 5000, 'start_extent_y': 5000, 
    #   'minimap_min_x': 569000, 'minimap_min_y': 380000, 
    #   'minimap_max_x': 599000, 'minimap_max_y': 410000
    # }
    def game_mode_change(self, response: dict):

        logger.info("the landscapelab tries to change the game mode")

        if "projection_epsg" in response:
            epsg = int(response["projection_epsg"])
        else:
            epsg = self.config.get("map_settings", "coordinate_reference_system")

        # calculate the main map extent based on the starting location
        start_position = Vector(float(response["start_position_x"]), float(response["start_position_y"]))
        width = float(response["start_extent_x"])
        height = float(response["start_extent_y"])
        start_extent = Extent.around_center(start_position, width, height/width)
        self.extent_tracker.map_extent = start_extent

        # setup the minimap extent
        mm_min_x = float(response["minimap_min_x"])
        mm_min_y = float(response["minimap_min_y"])
        mm_max_x = float(response["minimap_max_x"])
        mm_max_y = float(response["minimap_max_y"])
        minimap_extent = Extent(mm_min_x, mm_min_y, mm_max_x, mm_max_y)

        # change the maps
        self.mini_map.initialize_map(epsg, minimap_extent)
        self.main_map.initialize_map(epsg, start_extent)

        # reset the tracker and feed him the allowed brick combinations
        allowed_bricks = []
        for token_dict in response["used_tokens"]:
            shape = BrickShape[token_dict["shape"]]
            color = BrickColor[token_dict["color"]]
            icon_id = token_dict["icon_name"] 
            brick_config.icon_config[(token_dict["shape"], token_dict["color"])] = icon_id

            disappear = float(token_dict["disappear_after_seconds"])  # FIXME: to be implemented
            token = Token(shape, color, icon_id)  # FIXME: currently the svg is not implemented (coded via icon names)
            allowed_bricks.append(token)
        self.tracker.change_game_mode(allowed_bricks)

        # add new tokens
        for brick in response["existing_tokens"]:
            self.create_local_brick(brick)

        # create the scores for the new game mode
        scores = []
        for score_dict in response["scores"]:
            score_id = int(score_dict["score_id"])
            initial_value = float(score_dict["initial_value"])
            target_value = float(score_dict["target_value"])
            name = ""
            if score_dict["name"]:
                name = score_dict["name"]
            score = Score(score_id, target_value, initial_value, name)
            scores.append(score)
        UISetup.add_progressbars_to_ui(self.progressbars_ui, self.config, scores)

        # finally set to EXTERNAL ProgramStage
        self.program_stage.next()

    def create_local_brick(self, response: dict):
        shape = response["shape"]
        color = response["color"]
        token = Token(BrickShape[shape], color)
        new_brick = Brick(0, 0, token)  # centroid will be calculated later
        new_brick.status = BrickStatus.EXTERNAL_BRICK
        new_brick.object_id = int(response["object_id"])
        new_brick.map_pos_x = float(response["position_x"])
        new_brick.map_pos_y = float(response["position_y"])
        self.tracker.add_external_brick(new_brick)

    def update_local_brick(self, response: dict):
        object_id = int(response["object_id"])
        position_x = float(response["position_x"])
        position_y = float(response["position_y"])
        self.tracker.update_external_brick(object_id, position_x, position_y)

    def remove_local_brick(self, response: dict):
        object_id = int(response["object_id"])
        self.tracker.remove_external_brick(object_id)

    def update_local_score(self, response: dict):

        score_id = int(response["score_id"])
        value = float(response["value"])
        logger.info("the landscapelab sent a new value of {} for score {}".format(value, score_id))

        # FIXME: this logic should move somewhere where the UI is managed
        for progress_bar in self.progressbars_ui.get_by_type(ProgressBar):
            if hasattr(progress_bar, "score"):
                if progress_bar.score.score_id == score_id:
                    progress_bar.score.set_value(value)
