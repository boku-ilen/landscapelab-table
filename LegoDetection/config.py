import numpy as np

# Save video with shape detection output
video_output_name = "shape_detection_output.avi"

# Server communication settings
prefix = "http://"
ip = "127.0.0.1"
create_asset = "/landscapelab/assetpos/create/"
set_asset = "/landscapelab/assetpos/set/"
remove_asset = "/landscapelab/assetpos/remove/"
get_location = "/landscapelab/location/map/"
location_extension = ".json"

# Get board detection property
board_size_width = None
board_size_height = None

# QGIS interaction info
QGIS_IP = "127.0.0.1"
QGIS_READ_PORT = 5005
LEGO_READ_PORT = 5006
UDP_BUFFER_SIZE = 1024
QGIS_IMAGE_PATH = 'E:/Users/rotzr/Documents/Desktoperweiterungen/desktop/Arbeit/BOKU_2018/TestProjekte/QGIS_Remote/outputImage.png'
UPDATE_KEYWORD = 'update '
RENDER_KEYWORD = 'render '

# UI settings
start_extent = np.array([
    112518.16800000000512227, 275472.02100000000791624,
    685444.46299999998882413, 570431.06900000001769513
])
PAN_DISTANCE = 0.1
ZOOM_STRENGTH = 0.2     # TODO replace with arrays for different increments
