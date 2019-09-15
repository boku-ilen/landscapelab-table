import logging
import requests
import json

from .LegoBricks import LegoBrick, LegoStatus
from .LegoExtent import LegoExtent
from .ExtentTracker import ExtentTracker
from .ProgramStage import ProgramStage

# Configure logging
logger = logging.getLogger(__name__)

# Constants for server communication
HTTP = "http://"
PREFIX = "/landscapelab-dev"
CREATE_ASSET_POS = "/assetpos/create/"
SET_ASSET_POS = "/assetpos/set/"
REMOVE_ASSET_POS = "/assetpos/remove/"
GET_SCENARIO_INFO = "/location/scenario/list.json"
GET_INSTANCES = "/assetpos/get_all/"
JSON = ".json"

PLAYER_POSITION_ASSET_ID = str(13)


class ServerCommunication:
    """Creates and removes lego instances"""

    def __init__(self, config, program_stage):

        self.config = config
        self.program_stage = program_stage
        self.extent_tracker = ExtentTracker.get_instance()
        self.scenario_id = None

        # Initialize ip
        self.ip = self.config.get("server", "ip")

    # Check status code of the response
    # Return True if 200, else return False
    @staticmethod
    def check_status_code_200(status_code):

        # Check the status code
        # Return False if status code is not 200
        if status_code is not 200:
            logger.debug("request json status code: {}".format(status_code))
            return False

        # Return True if status code is 200
        return True

    # Create lego instance
    def create_lego_instance(self, lego_brick: LegoBrick):

        # Compute geographical coordinates for lego bricks
        LegoExtent.calc_world_pos(lego_brick, self.extent_tracker.board, self.extent_tracker.map_extent)

        # Map the lego brick asset_id from color & shape
        if self.program_stage.current_stage == ProgramStage.EVALUATION:
            lego_brick.map_evaluation_asset_id(self.config)
        else:
            lego_brick.map_asset_id(self.config)

        # Send request creating lego instance and save the response
        create_instance_msg = "{http}{ip}{prefix}{command}{scenario_id}/{brick_id}/{brick_x}/{brick_y}".format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=CREATE_ASSET_POS, scenario_id=self.scenario_id,
            brick_id=str(lego_brick.asset_id), brick_x=str(lego_brick.map_pos_x), brick_y=str(lego_brick.map_pos_y)
        )

        logger.debug(create_instance_msg)
        lego_instance_response = requests.get(create_instance_msg)

        # Check if status code is 200
        if self.check_status_code_200(lego_instance_response.status_code):

            # If status code is 200, save response text
            lego_instance_response_text = json.loads(lego_instance_response.text)

            # Match given instance id with lego brick id
            lego_instance_creation_success = lego_instance_response_text.get("creation_success")

            if lego_instance_creation_success:

                # Get assetpos_id in response
                lego_brick.assetpos_id = lego_instance_response_text.get("assetpos_id")

            else:
                # If the asset creation was not possible, set lego brick outdated
                lego_brick.status = LegoStatus.OUTDATED_BRICK

            logger.debug("creation_success: {}, assetpos_id: {}"
                         .format(lego_instance_creation_success, lego_brick.assetpos_id))

    # Remove lego instance
    def remove_lego_instance(self, lego_instance):

        # Send a request to remove lego instance
        logger.debug(HTTP + self.ip + PREFIX + REMOVE_ASSET_POS + str(lego_instance.assetpos_id))
        lego_remove_instance_response = requests.get(HTTP + self.ip
                                                     + PREFIX + REMOVE_ASSET_POS + str(lego_instance.assetpos_id))
        logger.debug("remove instance {}, response {}".format(lego_instance, lego_remove_instance_response))

    def get_scenario_info(self, scenario_name):
        scenario_request_msg = "{http}{ip}{prefix}{command}".format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=GET_SCENARIO_INFO
        )

        logger.debug(scenario_request_msg)
        request_return = requests.get(scenario_request_msg)

        if not self.check_status_code_200(request_return.status_code):
            raise ConnectionError("Bad request")

        scenarios = json.loads(request_return.text)

        for scenario_key in scenarios:
            scenario = scenarios[scenario_key]

            if scenario['name'] == scenario_name:
                # save scenario id for further communication
                self.scenario_id = scenario_key

                return scenario

        logger.error('Could not find scenario with name {}'.format(scenario_name))
        raise LookupError('No scenario with name {} exists'.format(scenario_name))

    def get_stored_lego_instances(self, asset_id):

        stored_instances_list = []

        stored_instances_msg = "{http}{ip}{prefix}{command}{asset_id}{json}".format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=GET_INSTANCES, asset_id=str(asset_id), json=JSON)

        stored_instances_response = requests.get(stored_instances_msg)

        # Check if status code is 200
        if self.check_status_code_200(stored_instances_response.status_code):
            # If status code is 200, save response text
            lego_instance_response_text = json.loads(stored_instances_response.text)
            stored_assets = lego_instance_response_text["assets"]

            # Save all instances with their properties as a list
            for assetpos_id in stored_assets:

                # Create a lego brick instance
                stored_instance = LegoBrick(None, None, None, None)

                # Get the map position of the player
                position = stored_assets[assetpos_id]["position"]
                stored_instance.map_pos_x = position[0]
                stored_instance.map_pos_y = position[1]

                # Map a shape and color using known asset_id
                shape_color = self.config.get("stored_instances", str(asset_id))
                shape = shape_color.split(', ')[0]
                color = shape_color.split(', ')[1]

                # Add missing properties
                stored_instance.shape = shape
                stored_instance.color = color
                stored_instance.asset_id = asset_id
                stored_instance.assetpos_id = assetpos_id
                stored_instance.status = LegoStatus.EXTERNAL_BRICK

                # Calculate map position of a brick
                LegoExtent.calc_local_pos(stored_instance, self.extent_tracker.board, self.extent_tracker.map_extent)

                stored_instances_list.append(stored_instance)

        return stored_instances_list

    # TODO: write stored instance and player position as a one method
    def get_player_position(self):

        player_instance = None

        player_position_msg = "{http}{ip}{prefix}{command}{asset_id}{json}".format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=GET_INSTANCES,
            asset_id=PLAYER_POSITION_ASSET_ID, json=JSON)

        player_position_response = requests.get(player_position_msg)

        # Check if status code is 200
        if self.check_status_code_200(player_position_response.status_code):
            # If status code is 200, save response text
            player_position_response_text = json.loads(player_position_response.text)

            assets = player_position_response_text["assets"]

            if assets is not None:

                # Save and return the player position
                for assetpos_id in assets:

                    # Create a lego brick instance
                    player_instance = LegoBrick(None, None, None, None)

                    # Get the map position of the player
                    player_position = assets[assetpos_id]["position"]
                    player_instance.map_pos_x = player_position[0]
                    player_instance.map_pos_y = player_position[1]

                    # Calculate the local position of the player
                    LegoExtent.calc_local_pos(player_instance, self.extent_tracker.board, self.extent_tracker.map_extent)

                    # Add missing properties
                    player_instance.asset_id = PLAYER_POSITION_ASSET_ID
                    player_instance.assetpos_id = assetpos_id
                    player_instance.status = LegoStatus.EXTERNAL_BRICK

        return player_instance
