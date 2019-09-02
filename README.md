# Setup

install python 3.6.8 (or 3.6.7 if corrupted)
install libraries if missing (see requirements.txt)
* at least at windows it is required to install libzbar0

for using life stream: 
	connect realsense camera 
	place four QR-codes to set the lego detection board

for using video (.bag) without camera:
	use an optional parameter 'usestream' with the .bag file name
(Note: .bag file can be recorded with RecordVideo/RecordVideo.py using realsense camera)

for saving the output as .avi file:
	def run(self, record_video=True):

# QGIS-Plugin
LegoLab is intended to run in conjunction with the QGIS-Plugin
[Remote Renderer](https://github.com/boku-ilen/landscapelab-qgis), which it uses to render the displayed map sections.
At the time of writing the connection between the two components is still a bit finicky. In case the issues will not be
patched out in time here are some short instructions on what to do and what to avoid doing when starting the
application:

It is generally advised to start the Remote Rendering process first and LegoLab second. When restarting LegoLab it is
usually not necessary to stop and restart the Remote Rendering process. However stopping and restarting the Remote
Rendering process while LegoLab is running will result in an Connection Error and QGIS will not be able to send messages
to LegoLab. To resolve this issue simply restart LegoLab.

 

# Run

DEPRECATED
run the server
start LegoDetection/LegoDetection.py

# Paramaters
Optional:
--threshold 
  set another then default threshold for black-white image to recognize qr-codes
--usestream USESTREAM
  path and name of the file with saved .bag stream

# Examples
python.exe (...)/LegoDetection/LegoDetection.py
(...)/python.exe (...)/LegoDetection/LegoDetection.py --usestream=stream.bag --threshold=155
