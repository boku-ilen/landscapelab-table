# NOTE since this script is executed in the QGIS-Python environment
#  PyCharm might wrongfully mark some libraries/classes as unknown
from PyQt5.QtGui import *
from PyQt5.QtCore import QSize
from qgis.core import *     # unsure if necessary
from qgis.utils import *    # unsure if necessary


# code from https://stackoverflow.com/questions/5731863/mapping-a-numeric-range-onto-another
def map_interval(in_value, in_interval_start, in_interval_end, out_interval_start, out_interval_end):

    slope = (out_interval_end - out_interval_start) / (in_interval_end - in_interval_start)
    out_value = out_interval_start + slope * (in_value - in_interval_start)
    return out_value


def convert_extent(full_map_extent, full_canvas_extent, canvas_extent):

    new_x_min = map_interval(canvas_extent.xMinimum(), full_canvas_extent.xMinimum(), full_canvas_extent.xMaximum(),
                             full_map_extent.xMinimum(), full_map_extent.xMaximum())
    new_x_max = map_interval(canvas_extent.xMaximum(), full_canvas_extent.xMinimum(), full_canvas_extent.xMaximum(),
                             full_map_extent.xMinimum(), full_map_extent.xMaximum())
    new_y_min = map_interval(canvas_extent.yMinimum(), full_canvas_extent.yMinimum(), full_canvas_extent.yMaximum(),
                             full_map_extent.yMinimum(), full_map_extent.yMaximum())
    new_y_max = map_interval(canvas_extent.yMaximum(), full_canvas_extent.yMinimum(), full_canvas_extent.yMaximum(),
                             full_map_extent.yMinimum(), full_map_extent.yMaximum())

    map_extent = QgsRectangle(new_x_min, new_y_min, new_x_max, new_y_max)
    return map_extent


# code from https://github.com/opensourceoptions/pyqgis-tutorials/blob/master/015_render-map-layer.py
def render_image(canvas, image_location):
    canvas_extent = canvas.extent()
    full_canvas_extent = canvas.fullExtent()

    ratio = canvas_extent.width() / canvas_extent.height()
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
    rect = QgsRectangle(convert_extent(ms.fullExtent(), full_canvas_extent, canvas_extent))
    # rect.scale(1.0)
    ms.setExtent(rect)

    # set ouptut size
    ms.setOutputSize(img.size())

    # setup qgis map renderer
    render = QgsMapRendererCustomPainterJob(ms, p)
    render.start()
    render.waitForFinished()
    p.end()

    # save the image
    img.save(image_location)