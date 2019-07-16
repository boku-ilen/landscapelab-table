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

# Max RGB resolution: 1920 x 1080 at 30 fps, depth: up to 1280 x 720, up to 90 fps
# For resolution 1280x720 and distance ~1 meter a short side of lego piece has ~14 px length
WIDTH: int = 1280
HEIGHT: int = 720
