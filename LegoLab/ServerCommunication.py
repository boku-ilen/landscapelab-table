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
GET_ENERGY_TARGET = "/energy/target/"
GET_ENERGY_CONTRIBUTION = "/energy/contribution/"
JSON = ".json"

PLAYER_POSITION_ASSET_ID = str(13)


class ServerCommunication:
    """Creates and removes lego instances"""

    def __init__(self, config, program_stage):

        self.config = config
        self.program_stage = program_stage
        self.extent_tracker = ExtentTracker.get_instance()
        self.scenario_id = None
        self.brick_update_callback = lambda: None

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

                # call brick update callback function to update progress bars etc.
                self.brick_update_callback()

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

        # call brick update callback function to update progress bars etc.
        self.brick_update_callback()

    def get_scenario_info(self, scenario_name):
        scenario_request_msg = "{http}{ip}{prefix}{command}".format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=GET_SCENARIO_INFO
        )

        logger.debug(scenario_request_msg)
        request_return = requests.get(scenario_request_msg)

        if not self.check_status_code_200(request_return.status_code):
            raise ConnectionError("Bad request: {}".format(scenario_request_msg))

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

            if stored_assets is not None:

                # Save all instances with their properties as a list
                for assetpos_id in stored_assets:

                    # Create a lego brick instance
                    stored_instance = LegoBrick(None, None, None, None)

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
                    stored_instance.status = LegoStatus.EXTERNAL_BRICK

                    # Calculate map position of a brick
                    LegoExtent.calc_local_pos(stored_instance, self.extent_tracker.board,
                                              self.extent_tracker.map_extent)

                    stored_instances_list.append(stored_instance)

        return stored_instances_list

    # initiates corner point update of the given main map extent on the server
    def update_extent_info(self, extent: LegoExtent):

        # get the corner IDs
        top_left_corner_id = self.config.get("server", "extent_top_left_corner_id")
        bot_right_corner_id = self.config.get("server", "extent_bottom_right_corner_id")

        # create the request messages
        create_top_left_msg = "{http}{ip}{prefix}{command}{scenario_id}/{asset_id}/{x}/{y}".format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=CREATE_ASSET_POS, scenario_id=self.scenario_id,
            asset_id=top_left_corner_id, x=str(extent.x_min), y=str(extent.y_min)
        )

        create_bot_right_msg = "{http}{ip}{prefix}{command}{scenario_id}/{asset_id}/{x}/{y}".format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=CREATE_ASSET_POS, scenario_id=self.scenario_id,
            asset_id=bot_right_corner_id, x=str(extent.x_max), y=str(extent.y_max)
        )

        logger.debug(create_top_left_msg)
        logger.debug(create_bot_right_msg)

        # send the messages
        tl_ret = requests.get(create_top_left_msg)
        br_ret = requests.get(create_bot_right_msg)

        # log warning if extent corners could not be updated
        if ((not self.check_status_code_200(tl_ret.status_code))
                or (not self.check_status_code_200(br_ret.status_code))):
            logger.warning("Could not update main map extent on server")

    # checks how much energy a given asset type contributes
    def get_energy_contrib(self, asset_type_id):

        # create msg
        get_asset_contrib_msg = '{http}{ip}{prefix}{command}{scenario_id}/{asset_type_id}.json'.format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=GET_ENERGY_CONTRIBUTION, scenario_id=self.scenario_id,
            asset_type_id=asset_type_id
        )

        logger.debug("getting energy contrib. for asset type {} with: {}".format(asset_type_id, get_asset_contrib_msg))

        # send msg
        contrib_return = requests.get(get_asset_contrib_msg)

        # check if request successful
        if not self.check_status_code_200(contrib_return.status_code):
            raise ConnectionError("Bad Request: {}".format(get_asset_contrib_msg))

        # return energy contribution
        return json.loads(contrib_return.text)['total_energy_contribution']

    # check how much energy a given asset type should contribute
    def get_energy_target(self, asset_type_id):

        # create msg
        get_asset_target_msg = '{http}{ip}{prefix}{command}{scenario_id}/{asset_type_id}.json'.format(
            http=HTTP, ip=self.ip, prefix=PREFIX, command=GET_ENERGY_TARGET, scenario_id=self.scenario_id,
            asset_type_id=asset_type_id
        )

        logger.debug("getting energy target for asset type {} with: {}".format(asset_type_id, get_asset_target_msg))

        # send msg
        target_return = requests.get(get_asset_target_msg)

        # check if request successful
        if not self.check_status_code_200(target_return.status_code):
            raise ConnectionError("Bad Request: {}".format(get_asset_target_msg))

        # return energy target
        return json.loads(target_return.text)['energy_target']