import argparse


class ParameterManager:

    used_stream = None

    def __init__(self, config):

        self.parse(config)

    def parse(self, config):

        # Parse optional parameters
        parser = argparse.ArgumentParser()
        parser.add_argument("--usestream", help="path and name of the file with saved .bag stream")
        parser.add_argument("--ip", help="overwrites default server ip defined in config")
        parser.add_argument("--starting_location", type=str,
                            help="overwrites default starting location defined in config")

        parser_arguments = parser.parse_args()

        if parser_arguments.usestream is not None:
            self.used_stream = parser_arguments.usestream

        if parser_arguments.ip is not None:
            config.set("server", "ip", parser_arguments.ip)

        if parser_arguments.starting_location is not None:
            config.set("general", "starting_location", parser_arguments.starting_location)
