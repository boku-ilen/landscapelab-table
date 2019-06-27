# Setup

install python 3.6.8 (or 3.6.7 if corrupted)

install libraries if missing (see requirements.txt):
cv2=3.3.1 (opencv)
pyrelasense (https://pypi.org/project/pyrealsense2/) on License: Apache 2.0.
pyzbar=0.1.8 (https://pypi.org/project/pyzbar/)
numpy
colorsys
logging
time
requests
config
shapely
json
scipy
collections
math
enum
argparse

for using life stream: 
	connect realsense camera 
	place four QR-codes to set the lego detection board

for using video (.bag) without camera:
	use an optional parameter 'usestream' with the .bag file name
(Note: .bag file can be recorded with RecordVideo/RecordVideo.py using realsense camera)

for saving the output as .avi file:
	def run(self, record_video=True):

# Run

run the server
start LegoDetection/LegoDetection.py

# Examples
python.exe (...)/LegoDetection/LegoDetection.py
(...)/python.exe (...)/LegoDetection/LegoDetection.py --usestream=stream.bag