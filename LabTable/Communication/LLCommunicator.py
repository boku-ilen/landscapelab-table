import logging
import json

from Configurator import Configurator
from LabTable.Communication.Communicator import Communicator
from LabTable.Model.Brick import Brick, BrickStatus
from LabTable.Model.Extent import Extent
from LabTable.ExtentTracker import ExtentTracker


# Configure logging
logger = logging.getLogger(__name__)

# remote communication protocol
GET_ASSETS_MSG = {
    "keyword": "GET_OBJECT_LAYER_DATA",
    "layer_name": ""
}
CREATE_ASSET_MSG = {
    "keyword": "CREATE_OBJECT",
    "layer_name": "",
    "position": [0.0, 0.0]
}
UPDATE_ASSET_MSG = {
    "keyword": "SET_OBJECT_POSITION",
    "layer_name": "",
    "object_id": 0,
    "position": [0.0, 0.0]
}
REMOVE_ASSET_MSG = {
    "keyword": "REMOVE_OBJECT",
    "layer_name": "",
    "object_id": 0
}
GET_SETTINGS_MSG = {
    "keyword": "GET_SETTINGS"
}
TELEPORT_TO_MSG = {
    "keyword": "TELEPORT_TO",
    "projected_x": 0.0,
    "projected_y": 0.0
}
SET_EXTENT_MSG = {
    "keyword": "TABLE_EXTENT",
    "min_x": 0.0,
    "min_y": 0.0,
    "max_x": 0.0,
    "max_y": 0.0
}

GET_ENERGY_TARGET = "/energy/target/"
GET_ENERGY_CONTRIBUTION = "/energy/contribution/"


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

        message = GET_SETTINGS_MSG
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
        message = CREATE_ASSET_MSG.copy()
        message["layer_name"] = brick.layer_id
        message["position"] = [brick.map_pos_x, brick.map_pos_y]

        self.send_message(message, create_callback)

    # Remove remote brick instance
    def remove_remote_brick_instance(self, brick_instance):

        def remove_callback(response: dict):

            if "success" in response:
                if response["success"]:

                    # call brick update callback function to update progress bars etc.
                    self.brick_update_callback()

                else:
                    logger.warning("could not remove remote brick {}".format(brick_instance))

        message = REMOVE_ASSET_MSG.copy()
        message["layer_name"] = brick_instance.layer
        message["object_id"] = brick_instance.object_id

        # Send a request to remove brick instance
        self.send_message(message, remove_callback)

    def get_stored_brick_instances(self, layer_name, result_callback):

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
                        shape_color = self.config.get(
                            "stored_instances", str(asset["id"]))
                        shape = shape_color.split(', ')[0]
                        color = shape_color.split(', ')[1]
                    except:
                        logger.info("Mapping of color and shape for asset_id {} is not possible".format(
                            str(asset["id"])))

                    # Add missing properties
                    stored_instance.shape = shape
                    stored_instance.color = color
                    stored_instance.layer_id = layer_name
                    stored_instance.object_id = asset["id"]
                    stored_instance.status = BrickStatus.EXTERNAL_BRICK

                    # Calculate map position of a brick
                    Extent.calc_local_pos(stored_instance, self.extent_tracker.board,
                                          self.extent_tracker.map_extent)

                    stored_instances_list.append(stored_instance)

            result_callback(stored_instances_list)

        logger.debug("getting stored brick instances from the server...")

        message = GET_ASSETS_MSG.copy()
        message["layer_name"] = layer_name

        self.send_message(message, get_instances_callback)

    # initiates corner point update of the given main map extent
    # and informs the LandscapeLab
    def update_extent_info(self, extent: Extent):

        def extent_callback(response: dict):
            pass

        message = SET_EXTENT_MSG.copy()
        message["min_x"] = extent.x_min
        message["min_y"] = extent.y_min
        message["max_x"] = extent.x_max
        message["max_y"] = extent.y_max

        self.send_message(message, extent_callback)

    # checks how much energy a given asset type contributes
    # FIXME: this has to be generalized to work with various game objects
    def get_energy_contrib(self, asset_type_id):

        # create msg
        get_asset_contrib_msg = '{command}{scenario_id}/{asset_type_id}.json'.format(
            command=GET_ENERGY_CONTRIBUTION, scenario_id=self.scenario_id, asset_type_id=asset_type_id)

        # send msg
        contrib_return = self.send_message(get_asset_contrib_msg)

        # check if request successful
        # FIXME: rework protocol
        if not self.check_status_code_200(contrib_return.status_code):
            raise ConnectionError(
                "Bad Request: {}".format(get_asset_contrib_msg))

        # return energy contribution
        return json.loads(contrib_return.text)['total_energy_contribution']

    # check how much energy a given asset type should contribute
    # FIXME: this has to be generalized to work with various game objects
    def get_energy_target(self, asset_type_id):

        # create msg
        get_asset_target_msg = '{command}{scenario_id}/{asset_type_id}.json'.format(
            command=GET_ENERGY_TARGET, scenario_id=self.scenario_id, asset_type_id=asset_type_id)

        # send msg
        target_return = self.send_message(get_asset_target_msg)

        # check if request successful
        # FIXME: rework protocol

        # return energy target
        # return json.loads(target_return.text)['energy_target']
