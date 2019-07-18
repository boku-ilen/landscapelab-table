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
"""" # full extent
start_extent = np.array([
    9.2, 45.3,
    17.5, 49.9
])
"""
# bisamberg
start_extent = np.array([
    16.31177944684454, 48.30538963724319,
    16.403183681038215, 48.35604740559146
])

PAN_DISTANCE = 0.1
ZOOM_STRENGTH = 0.2     # TODO replace with arrays for different increments
