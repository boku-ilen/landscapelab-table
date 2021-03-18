import logging
import threading
from typing import Optional

import websocket
import ssl
import json

from Configurator import ConfigError
from LabTable.Model.Brick import Brick, BrickStatus
from LabTable.Model.Extent import Extent
from .ExtentTracker import ExtentTracker
from LabTable.Model.ProgramStage import ProgramStage

# Configure logging
logger = logging.getLogger(__name__)

# remote communication protocol
URL = "ws{s}://{host}:{port}"  # this is a websocket (ssl) connection
CREATE_ASSET_MSG = {
    "keyword": "FEATURE_CREATE",
    "layer": "",
    "etrs_x": 0.0,
    "etrs_y": 0.0
}
UPDATE_ASSET_MSG = {
    "keyword": "FEATURE_UPDATE",
    "layer": "",
    "object_id": 0,
    "etrs_x": 0.0,
    "etrs_y": 0.0
}
REMOVE_ASSET_MSG = {
    "keyword": "FEATURE_REMOVE",
    "layer": "",
    "object_id": 0
}
GET_SCENARIOS_MSG = {
    "keyword": "GET_SCENARIOS"
}
TELEPORT_TO_MSG = {
    "keyword": "TELEPORT_TO",
    "etrs_x": 0.0,
    "etrs_y": 0.0
}
SET_EXTENT_MSG = {
    "keyword": "TABLE_EXTENT",
    "min_x": 0.0,
    "min_y": 0.0,
    "max_x": 0.0,
    "max_y": 0.0
}

ANSWER_STRING = "REQUEST_RESULT"
ASSETPOS_ID_STRING = "ASSETPOS_ID"
SUCCESS_ANSWER = "SUCCESS"
FAILURE_ANSWER = "FAILURE"

GET_INSTANCES = "/assetpos/get_all/"
GET_ENERGY_TARGET = "/energy/target/"
GET_ENERGY_CONTRIBUTION = "/energy/contribution/"


class Communicator(threading.Thread):
    """Creates and removes remote brick instances"""

    _uri = None
    _ssl_context = None
    _connection_instance = None
    _connection_open = False

    def __init__(self, config, program_stage):

        # call super()
        threading.Thread.__init__(self)
        self.name = "[LabTable] Communicator"

        self.config = config
        self.program_stage = program_stage  # FIXME: the program stage should be managed remotely now!
        self.extent_tracker = ExtentTracker.get_instance()
        self.scenario_id = None
        self.brick_update_callback = lambda: None
        self._ssl_context = None

        # initialize connection string and ssl configuration
        ip = self.config.get("server", "ip")
        port = self.config.get("server", "port")
        ssl_pem_file = self.config.get("server", "ssl_pem_file")

        # if ssl is configured load the pem file
        s = ""
        if ssl_pem_file:
            self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            try:
                self._ssl_context.load_verify_locations(ssl_pem_file)
                s = "s"
            except FileNotFoundError:
                logger.fatal("SSL file configured but not found: {}".format(ssl_pem_file))
                raise ConfigError("SSL file configured but not found: {}".format(ssl_pem_file))

        self._uri = URL.format(s=s, host=ip, port=port)
        logger.info("configured remote URL to {}".format(self._uri))

        # start the listener thread
        self.start()

    def on_message(self, ws, message):
        print(message)

    def on_error(self, ws, error):
        logger.error(error)
        self._connection_open = False

    def on_close(self, ws):
        self._connection_open = False

    def on_open(self, ws):
        self._connection_open = True

    def close(self):
        self._connection_instance.close()
        logger.info("closing websocket connection")

    # starting the listener thread and perform the connection to the LandscapeLab!
    def run(self):

        # try to connect to server
        self._connection_instance = websocket.WebSocketApp(self._uri, on_close=self.on_close,
                                                           on_message=self.on_message, on_open=self.on_open,
                                                           on_error=self.on_error)
        self._connection_instance.run_forever()

    # this sends an message to the server and returns the json answer
    def send_message(self, message: dict) -> Optional[dict]:

        logger.debug("sending message: {}".format(message))

        if self._connection_open:
            self._connection_instance.send(message)
            ret = self._connection_instance.recv()
            logger.debug("received message: {}".format(ret))

            # we expect json answers only
            return json.loads(ret)

        else:
            logger.error("Could not send message as there is no connection to the LandscapeLab!")
            return None

    # Create remote brick instance
    def create_remote_brick_instance(self, brick: Brick):

        logger.debug("creating a brick instance for {}".format(brick))

        # Compute geographical coordinates for bricks
        Extent.calc_world_pos(brick, self.extent_tracker.board, self.extent_tracker.map_extent)

        # Map the brick asset_id from color & shape
        # FIXME: generalize ProgramStage logic
        if self.program_stage.current_stage == ProgramStage.EVALUATION:
            brick.map_evaluation_asset_id(self.config)
        else:
            brick.map_asset_id(self.config)

        # Send request creating remote brick instance and save the response
        message = CREATE_ASSET_MSG.copy()
        message["layer"] = brick.layer_id
        message["etrs_x"] = brick.map_pos_x
        message["etrs_y"] = brick.map_pos_y

        threading.Thread("[LabTable] ", self.send_message(message))
        if response.get(ANSWER_STRING) is SUCCESS_ANSWER:

            # Get assetpos_id in response
            brick.object_id = response.get(ASSETPOS_ID_STRING)

            # call brick update callback function to update progress bars etc.
            self.brick_update_callback()

        # If the asset creation was not possible, set brick outdated
        else:
            logger.warning("could not remotely create brick {}".format(brick))
            brick.status = BrickStatus.OUTDATED_BRICK

    # Remove remote brick instance
    def remove_remote_brick_instance(self, brick_instance):

        message = REMOVE_ASSET_MSG.copy()
        message["layer"] = brick_instance.layer
        message["object_id"] = brick_instance.object_id

        # Send a request to remove brick instance
        response = self.send_message(message)

        if response.get(ANSWER_STRING) == SUCCESS_ANSWER:

            # call brick update callback function to update progress bars etc.
            self.brick_update_callback()

        else:
            logger.warning("could not remove remote brick {}".format(brick_instance))

    def get_scenario_info(self, scenario_name):

        # request_return = self.send_message("{}".format(GET_SCENARIO_INFO))

        # FIXME: rework protocol
        scenarios = {}  # WAS = json.loads(request_return.text)

        for scenario_key in scenarios:
            scenario = scenarios[scenario_key]

            if scenario['name'] == scenario_name:
                # save scenario id for further communication
                self.scenario_id = scenario_key

                return scenario

        logger.error('Could not find scenario with name {}'.format(scenario_name))
        # FIXME WAS: raise LookupError('No scenario with name {} exists'.format(scenario_name))

    def get_stored_brick_instances(self, asset_id):

        logger.debug("getting stored brick instances from the server...")

        stored_instances_list = []

        stored_instances_msg = "{command}{asset_id}{json}".format(command=GET_INSTANCES, asset_id=str(asset_id),
                                                                  json=JSON)
        stored_instances_response = self.send_message(stored_instances_msg)

        # FIXME: rework protocol
        # If status code is 200, save response text
        bricks_instance_response_text = json.loads(stored_instances_response.text)
        stored_assets = bricks_instance_response_text["assets"]

        if stored_assets is not None:

            # Save all instances with their properties as a list
            for assetpos_id in stored_assets:

                # Create a brick instance
                stored_instance = Brick(None, None, None, None)

                # Get the map position of the player
                position = stored_assets[assetpos_id]["position"]
                stored_instance.map_pos_x = position[0]
                stored_instance.map_pos_y = position[1]

                shape = None
                color = None
                try:
                    # Map a shape and color using known asset_id
                    shape_color = self.config.get("stored_instances", str(asset_id))
                    shape = shape_color.split(', ')[0]
                    color = shape_color.split(', ')[1]
                except:
                    logger.info("Mapping of color and shape for asset_id {} is not possible".format(str(asset_id)))

                # Add missing properties
                stored_instance.shape = shape
                stored_instance.color = color
                stored_instance.layer_id = asset_id
                stored_instance.object_id = assetpos_id
                stored_instance.status = BrickStatus.EXTERNAL_BRICK

                # Calculate map position of a brick
                Extent.calc_local_pos(stored_instance, self.extent_tracker.board,
                                      self.extent_tracker.map_extent)

                stored_instances_list.append(stored_instance)

        return stored_instances_list

    # initiates corner point update of the given main map extent
    # and informs the LandscapeLab
    def update_extent_info(self, extent: Extent):

        message = SET_EXTENT_MSG.copy()
        message["min_x"] = extent.x_min
        message["min_y"] = extent.y_min
        message["max_x"] = extent.x_max
        message["max_y"] = extent.y_max

        self.send_message(message)

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
            raise ConnectionError("Bad Request: {}".format(get_asset_contrib_msg))

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
