import json


# FIXME: why is this implemented as class, while all methods are defined
# FIXME: as static?
class JsonParser:

    def __init__(self):
        pass

    # Convert corner coordinates to int
    # if given in form: ((1516000 5935000, 1532000 5935000, 1532000 5913000, 1516000 5913000, 1516000 5935000))
    @staticmethod
    def parse_corner_coordinates(corner):

        corner_coordinates = corner.split(' ')

        # Convert list into string
        corner_x = int(''.join(corner_coordinates[0]))
        corner_y = int(''.join(corner_coordinates[1]))

        corner_coordinates = corner_x, corner_y

        return corner_coordinates

    # Return a dictionary with corners coordinates
    @staticmethod
    def parse(location_data):

        # Extract coordinates
        bbox = json.loads(location_data['bounding_box'])
        bbox_coordinates = bbox['coordinates'][0]

        # Save coordinates x, y as (int, int) in a dictionary
        bbox_polygon_dict = {
            'C_TL': bbox_coordinates[0],
            'C_TR': bbox_coordinates[1],
            'C_BR': bbox_coordinates[2],
            'C_BL': bbox_coordinates[3]
        }

        # TODO: check if coordinates matched properly the corners

        return bbox_polygon_dict
