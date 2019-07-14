# NOTE since this script is executed in the QGIS-Python environment
#  PyCharm might wrongfully mark some libraries/classes as unknown
from PyQt5.QtGui import *
from PyQt5.QtCore import QSize
from qgis.core import *     # unsure if necessary
from qgis.utils import *    # unsure if necessary


# code from https://github.com/opensourceoptions/pyqgis-tutorials/blob/master/015_render-map-layer.py
def render_image(extent, image_location):

    ratio = extent.width() / extent.height()
    image_width = 1920

    # create image
    img = QImage(QSize(image_width, image_width / ratio), QImage.Format_ARGB32_Premultiplied)

    # set background color
    color = QColor(255, 255, 255, 255)
    img.fill(color.rgba())

    # create painter
    p = QPainter()
    p.begin(img)
    p.setRenderHint(QPainter.Antialiasing)

    # create map settings
    ms = QgsMapSettings()
    ms.setBackgroundColor(color)

    # set layers to render
    layer = QgsProject.instance().mapLayersByName('Oesterreich_BEV_VGD_LAM')
    ms.setLayers([layer[0]])
    # TODO: set correct layers

    # set extent
    ms.setExtent(extent)

    # set output size
    ms.setOutputSize(img.size())

    # setup qgis map renderer
    render = QgsMapRendererCustomPainterJob(ms, p)
    render.start()
    render.waitForFinished()
    p.end()

    # save the image
    img.save(image_location)