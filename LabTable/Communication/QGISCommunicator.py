import logging

from TableUI.MapHandler import MapHandler
from LabTable.Configurator import Configurator
from LabTable.Model.Extent import Extent
from LabTable.Communication.Communicator import Communicator

# Configure logging
logger = logging.getLogger(__name__)

# remote communication protocol
RENDER_REQUEST_MSG = {
    "keyword": "RENDER",
    "target": "",
    "resolution": 0,
    "crs": "",
    "extent": {
        "x_min": 0.0,
        "y_min": 0.0,
        "x_max": 0.0,
        "y_max": 0.0
    }
}


# handles the communication with the qgis plugin
class QGISCommunicator(Communicator):

    callbacks: dict = None

    def __init__(self, config: Configurator, callbacks: dict):

        # initialize connection string and ssl configuration
        self.ip = config.get("qgis", "ip")
        self.port = config.get("qgis", "port")
        self.ssl_pem_file = config.get("server", "ssl_pem_file")

        # call super
        super().__init__(config)

        self.callbacks = callbacks

    # requests a new rendered map extent from qgis plugin
    def request_render(self, map_handler: MapHandler, extent: Extent = None):

        def render_callback(response: dict):

            extent = Extent(float(response["extent"]["x_min"]),
                            float(response["extent"]["y_min"]),
                            float(response["extent"]["x_max"]),
                            float(response["extent"]["y_max"]),
                            True)

            self.callbacks[response["target"]].refresh(extent, buffer)

        if extent is None:
            extent = map_handler.current_extent

        ret = RENDER_REQUEST_MSG
        ret["target"] = map_handler.name
        ret["resolution"] = map_handler.resolution_x
        ret["crs"] = map_handler.crs
        ret["extent"]["x_min"] = extent.x_min
        ret["extent"]["y_min"] = extent.y_min
        ret["extent"]["x_max"] = extent.x_max
        ret["extent"]["y_max"] = extent.y_max

        self.send_message(ret, render_callback)
