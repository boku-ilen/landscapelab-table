import json


class JsonParser:

    def __init__(self):
        pass

    # Convert corner coordinates to int
    @staticmethod
    def parse_corner_coordinates(corner):

        corner_coordinates = corner.split(' ')

        # Convert list into string
        corner_x = int(''.join(corner_coordinates[0]))
        corner_y = int(''.join(corner_coordinates[1]))

        corner_coordinates = corner_x, corner_y

        return corner_coordinates

    def parse(self, map_id):

        # Using file will be removed when json json from the server used
        with open('./ParseJSON/nockberge_maps.json') as f:
            location_data = json.load(f)

        bbox_polygon_dict = None

        for location_dict in location_data:

            if location_dict['pk'] == int(map_id):
                bbox = location_dict['fields']['bounding_box']
                bbox_polygon = bbox.split('((', 1)[1].split(')')[0]

                # Save coordinates x, y as (int, int) in a dictionary
                bbox_polygon_dict = {
                    'C_TL': self.parse_corner_coordinates(bbox_polygon.split(', ')[0]),
                    'C_TR': self.parse_corner_coordinates(bbox_polygon.split(', ')[1]),
                    'C_BR': self.parse_corner_coordinates(bbox_polygon.split(', ')[2]),
                    'C_BL': self.parse_corner_coordinates(bbox_polygon.split(', ')[3])
                }

        return bbox_polygon_dict
