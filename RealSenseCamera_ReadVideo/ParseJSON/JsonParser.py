import json


class JsonParser:

    def __init__(self):
        pass

    @staticmethod
    def parse(map_id):

        # Using file will be removed when json json from the server used
        with open('./ParseJSON/nockberge_maps.json') as f:
            location_data = json.load(f)

        bbox_polygon_dict = None

        for location_dict in location_data:

            if location_dict['pk'] == int(map_id):
                bbox = location_dict['fields']['bounding_box']
                bbox_polygon = bbox.split('((', 1)[1].split(')')[0]

                bbox_polygon_dict = {
                    'C_TL': bbox_polygon.split(', ')[0],
                    'C_TR': bbox_polygon.split(', ')[1],
                    'C_BL': bbox_polygon.split(', ')[2],
                    'C_BR': bbox_polygon.split(', ')[3]
                }

        return bbox_polygon_dict
