import os
from powerpan.power_pan_dockwidget import PowerPanDockWidget
from qgis.core import *
from qgis.utils import *
from functools import partial

"""
NOTE: in order for this script to work, the QGIS plugin PowerPan has to be installed

To run this make sure that the path to this file is included in sys.path
then call 'import QGIS_POC1' in the QGIS pyton console
"""


class Task:

	def __init__(self):
		# define image path
		self.image_location = os.path.join(QgsProject.instance().homePath(), 'outputImage.png')

		# setup power pan plugin
		self.ppdw = PowerPanDockWidget(iface)
		# define how far the view should move (how much of the previous viewport should still be visible in percent)
		self.ppdw.txt_hoverlap.setText('0')
		self.ppdw.txt_voverlap.setText('0')

		self.i = 0
		
		# every time the map has finished rendering call do_it()
		iface.mapCanvas().mapCanvasRefreshed.connect(partial(self.do_it))

	# saves the current viewport to an image every time it gets updated
	def do_it(self):
		# save image
		iface.mapCanvas().saveAsImage(self.image_location, None, "PNG")

		# for the first 30 times the map has been rerendered, shift the viewport to initiate a new render process
		if self.i < 30:
			# control view
			self.ppdw.btn_left_pressed()
			self.i += 1


t = Task()
t.do_it()
