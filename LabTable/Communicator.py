
# FIXME: THIS CLASS WILL BE COMPLETELY REWORKED TO COMMUNICATE WITH THE CLIENT DIRECTLY

import logging
import websockets
import asyncio
import ssl
import json

from LabTable.Model.Brick import Brick, BrickStatus
from LabTable.Model.Extent import Extent
from .ExtentTracker import ExtentTracker
from LabTable.Model.ProgramStage import ProgramStage

# Configure logging
logger = logging.getLogger(__name__)

# remote communication protocol
URI = "wss://{}:{}"  # this is a websocket ssl connection
CREATE_ASSET_MSG = "ASSETPOS_CREATE {brick_id} {brick_x} {brick_y}"
UPDATE_ASSET_MSG = "ASSETPOS_UPDATE {brick_id} {brick_x} {brick_y}"
REMOVE_ASSET_MSG = "ASSETPOS_REMOVE {brick_id}"
ANSWER_STRING = "REQUEST_RESULT"
ASSETPOS_ID_STRING = "ASSETPOS_ID"
SUCCESS_ANSWER = "SUCCESS"
FAILURE_ANSWER = "FAILURE"
GET_SCENARIO_INFO = "/location/scenario/list.json"
GET_INSTANCES = "/assetpos/get_all/"
GET_ENERGY_TARGET = "/energy/target/"
GET_ENERGY_CONTRIBUTION = "/energy/contribution/"


class Communicator:
    """Creates and removes remote brick instances"""

    _uri = None
    _ssl_context = None

    def __init__(self, config, program_stage):

        self.config = config
        self.program_stage = program_stage  # FIXME: the program stage should be managed remotely now!
        self.extent_tracker = ExtentTracker.get_instance()
        self.scenario_id = None
        self.brick_update_callback = lambda: None

        # initialize connection string and ssl configuration
        ip = self.config.get("server", "ip")
        port = self.config.get("server", "port")
        ssl_pem_file = self.config.get("server", "ssl_pem_file")
        self._uri = URI.format(ip, port)
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._ssl_context.load_verify_locations(ssl_pem_file)

    # this sends an message to the server and returns the json answer
    async def send_message(self, message: str) -> json:

        async with websockets.connect( self._uri, ssl=self._ssl_context) as websocket:

            logger.debug("sending message: {}".format(message))
            await websocket.send(message)
            ret = await websocket.recv()
            logger.debug("received message: {}".format(ret))

            # we expect json answers only
            return json.loads(ret)

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
        create_instance_msg = CREATE_ASSET_MSG.format(
            brick_id=str(brick.asset_id), brick_x=str(brick.map_pos_x), brick_y=str(brick.map_pos_y)
        )

        response = self.send_message(create_instance_msg)
        if response.get(ANSWER_STRING) is SUCCESS_ANSWER:

            # Get assetpos_id in response
            brick.assetpos_id = response.get(ASSETPOS_ID_STRING)

            # call brick update callback function to update progress bars etc.
            self.brick_update_callback()

        else:

            # If the asset creation was not possible, set brick outdated
            logger.warning("could not remotely create brick {}".format(brick))
            brick.status = BrickStatus.OUTDATED_BRICK

    # Remove remote brick instance
    def remove_remote_brick_instance(self, brick_instance):

        # Send a request to remove brick instance
        response = self.send_message(REMOVE_ASSET_MSG.format(brick_instance.assetpos_id))

        if response.get(ANSWER_STRING) == SUCCESS_ANSWER:

            # call brick update callback function to update progress bars etc.
            self.brick_update_callback()

        else:
            logger.warning("could not remove remote brick {}".format(brick_instance))

    def get_scenario_info(self, scenario_name):

        request_return = self.send_message("{}".format(GET_SCENARIO_INFO))

        # FIXME: rework protocol
        scenarios = json.loads(request_return.text)

        for scenario_key in scenarios:
            scenario = scenarios[scenario_key]

            if scenario['name'] == scenario_name:
                # save scenario id for further communication
                self.scenario_id = scenario_key

                return scenario

        logger.error('Could not find scenario with name {}'.format(scenario_name))
        raise LookupError('No scenario with name {} exists'.format(scenario_name))

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
                stored_instance.asset_id = asset_id
                stored_instance.assetpos_id = assetpos_id
                stored_instance.status = BrickStatus.EXTERNAL_BRICK

                # Calculate map position of a brick
                Extent.calc_local_pos(stored_instance, self.extent_tracker.board,
                                      self.extent_tracker.map_extent)

                stored_instances_list.append(stored_instance)

        return stored_instances_list

    # initiates corner point update of the given main map extent on the server
    def update_extent_info(self, extent: Extent):

        # get the corner IDs
        top_left_corner_id = self.config.get("server", "extent_top_left_corner_id")
        bot_right_corner_id = self.config.get("server", "extent_bottom_right_corner_id")

        # create the request messages
        create_top_left_msg = "{command}{scenario_id}/{asset_id}/{x}/{y}".format(
            command=CREATE_ASSET_POS, scenario_id=self.scenario_id,
            asset_id=top_left_corner_id, x=str(extent.x_min), y=str(extent.y_min)
        )

        create_bot_right_msg = "{command}{scenario_id}/{asset_id}/{x}/{y}".format(
            command=CREATE_ASSET_POS, scenario_id=self.scenario_id,
            asset_id=bot_right_corner_id, x=str(extent.x_max), y=str(extent.y_max)
        )

        # send the messages
        tl_ret = self.send_message(create_top_left_msg)
        br_ret = self.send_message(create_bot_right_msg)

        # log warning if extent corners could not be updated
        # FIXME: rework protocol
        if ((not self.check_status_code_200(tl_ret.status_code))
                or (not self.check_status_code_200(br_ret.status_code))):
            logger.warning("Could not update main map extent on server")

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
        return json.loads(target_return.text)['energy_target']
