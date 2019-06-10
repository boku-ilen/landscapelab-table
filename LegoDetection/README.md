# Setup

install python 3.6.8

install libraries if missing (see requirements.txt):
cv2=3.3.1 (opencv)
pyrelasense=2.20.0.714 (https://pypi.org/project/pyrealsense2/) on License: Apache 2.0.
pyzbar=0.1.8 (https://pypi.org/project/pyzbar/)
numpy
colorsys
logging
time
requests
config
shapely
json
scipy.spatial
collections
math
enum

for using life stream: 
	connect realsense camera 
	LegoDetection/LegoDetection.py: def __init__(self, use_video=False)
	place four QR-codes to set the lego detection board

for using video (.bag) without camera:
	LegoDetection/LegoDetection.py: def __init__(self, use_video=True)
	update .bag filename in STREAM_NAME variable
	save .bag file in LegoDetection folder
(Note: .bag file can be reocorded with RecordVideo/RecordVideo.py using realsense camera)

for saving the output as .avi file:
	def run(self, record_video=True):

# Run

run the server
start LegoDetection/LegoDetection.py