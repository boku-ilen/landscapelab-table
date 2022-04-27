import logging

from Configurator import Configurator
from LabTable.Communication.Communicator import Communicator
from LabTable.Model.Brick import Brick, BrickStatus
from LabTable.Model.Extent import Extent
from LabTable.ExtentTracker import ExtentTracker


# Configure logging
logger = logging.getLogger(__name__)

# remote communication protocol
GET_ASSETS_MSG = {
    "keyword": "GET_OBJECT_LAYER_DATA",  # FIXME: do we need this? could be provided during ProgramStage update?
}
CREATE_OBJECT_MSG = {
    "keyword": "CREATE_OBJECT",
    "position": [0.0, 0.0],
    "brick_color": None,
    "brick_shape": None
}
UPDATE_OBJECT_MSG = {
    "keyword": "SET_OBJECT_POSITION",  # FIXME: could other parameters be changed by the LabTable?
    "object_id": 0,
    "position": [0.0, 0.0]
}
REMOVE_OBJECT_MSG = {
    "keyword": "REMOVE_OBJECT",
    "object_id": 0
}
OBJECT_ANSWER_MSG = {  # FIXME: do we need more parameters? or do we transfer the serialized Brick-Object?
    "keyword": "OBJECT_ANSWER",
    "success": False,
    "object_id": 0
}
HANDSHAKE_MSG = {
    "keyword": "HANDSHAKE",
    "detected_brick_shapes": [],  # FIXME: or is it necessary to provide the combination of shape and color?
    "detected_brick_colors": []
}
UPDATE_GAMESTAGE_MSG = {
    "keyword": "CHANGE_GAMESTAGE",
    "used_brick_types": [],
}
SET_EXTENT_MSG = {  # this is sent on change to the LL
    "keyword": "TABLE_EXTENT",
    "min_x": 0.0,
    "min_y": 0.0,
    "max_x": 0.0,
    "max_y": 0.0
}
PLAYER_POSITION_MSG = {  # this is received on change from LL
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

        message = HANDSHAKE_MSG
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
        message = CREATE_OBJECT_MSG.copy()
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

        message = REMOVE_OBJECT_MSG.copy()
        message["object_id"] = brick_instance.object_id

        # Send a request to remove brick instance
        self.send_message(message, remove_callback)

    def get_stored_brick_instances(self, result_callback):

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

        message = SET_EXTENT_MSG.copy()
        message["min_x"] = extent.x_min
        message["min_y"] = extent.y_min
        message["max_x"] = extent.x_max
        message["max_y"] = extent.y_max

        self.send_message(message, extent_callback)

    # FIXME: this is only a protype
    # update the player position on the display where the landscapelab player(s) are positioned
    def update_player_position(self, player_id, pos_x, pos_y, pos_z, dir_x, dir_y, dir_z):
        pass
