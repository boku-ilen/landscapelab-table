import logging

from Configurator import Configurator
from LabTable.Communication.Communicator import Communicator
from LabTable.Model.Brick import Brick, BrickStatus
from LabTable.Model.Extent import Extent
from LabTable.ExtentTracker import ExtentTracker


# Configure logging
logger = logging.getLogger(__name__)

# remote communication protocol from/to the LL
SEND_REC_CREATE_OBJECT_MSG = {
    "keyword": "NEW_TOKEN",
    "position_x": 0.0,
    "position_y": 0.0,
    "token": {
        "shape": "",
        "color": ""
    },
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
    "success": False,
    "object_id": 0,
    "data": []  # optional for later (provide additional information)
}
SEND_HANDSHAKE_MSG = {
    "keyword": "TABLE_HANDSHAKE",
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
    "score_id": 0,
    "value": 0.0
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

    def __init__(self, config: Configurator):

        # call super()
        self.ip = config.get("landscapelab", "ip")
        self.port = config.get("landscapelab", "port")
        super().__init__(config)

        self.extent_tracker = ExtentTracker.get_instance()
        self.brick_update_callback = lambda: None

    def on_open(self, ws):
        super().on_open(ws)
        self.get_labtable_settings()

    # get the initial configuration settings related to the LabTable from the LL
    def get_labtable_settings(self):

        # store the settings we later got as answer in our configuration
        def settings_callback(response: dict):
            for key in response:
                group, entry = key.split("-")
                self.config.set(group, entry, response[key])

        message = SEND_HANDSHAKE_MSG
        # TODO: maybe fetch information about own system and send it to the LL
        self.send_message(message, settings_callback)

    # Create remote brick instance
    def create_remote_brick_instance(self, brick: Brick):

        def create_callback(response: dict):

            if "success" in response:
                if response["success"]:

                    # set the remote asset id
                    brick.object_id = response["id"]

                    # call brick update callback function to update progress bars etc.
                    self.brick_update_callback()

                else:
                    # TODO: which loglevel as not allowed to create a brick is a normal usecase
                    logger.info("could not remotely create brick {}".format(brick))
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

            if "success" in response:
                if response["success"]:

                    # call brick update callback function to update progress bars etc.
                    self.brick_update_callback()

                else:
                    logger.warning("could not remove remote brick {}".format(brick_instance))

        message = SEND_REC_REMOVE_OBJECT_MSG.copy()
        message["object_id"] = brick_instance.object_id

        # Send a request to remove brick instance
        self.send_message(message, remove_callback)

    def get_stored_brick_instances(self, result_callback):

        # FIXME: Can probably be removed

        def get_instances_callback(response: dict):
            stored_assets = response["objects"]
            stored_instances_list = []

            if stored_assets is not None:

                # Save all instances with their properties as a list
                for asset in stored_assets:

                    # Create a brick instance
                    stored_instance = Brick(None, None, None, None)

                    # Get the map position of the player
                    position = asset["position"]
                    stored_instance.map_pos_x = position[0]
                    stored_instance.map_pos_y = position[1]

                    shape = None
                    color = None
                    try:
                        # Map a shape and color using known asset_id
                        shape_color = self.config.get("stored_instances", str(asset["id"]))
                        shape = shape_color.split(', ')[0]
                        color = shape_color.split(', ')[1]
                    except:
                        logger.info("Mapping of color and shape for asset_id {} is not possible".format(
                            str(asset["id"])))

                    # Add missing properties
                    stored_instance.shape = shape
                    stored_instance.color = color
                    stored_instance.object_id = asset["id"]
                    stored_instance.status = BrickStatus.EXTERNAL_BRICK

                    # Calculate map position of a brick
                    Extent.calc_local_pos(stored_instance, self.extent_tracker.board, self.extent_tracker.map_extent)
                    stored_instances_list.append(stored_instance)

            result_callback(stored_instances_list)

        logger.debug("getting stored brick instances from the server...")

        message = GET_ASSETS_MSG.copy()
        self.send_message(message, get_instances_callback)

    # initiates corner point update of the given main map extent
    # and informs the LandscapeLab
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

    # FIXME: this is only a protype
    # update the player position on the display where the landscapelab player(s) are positioned
    def update_player_position(self, player_id, pos_x, pos_y, pos_z, dir_x, dir_y, dir_z):
        pass
