"""
Main file
"""


import bpy
import json
import argparse


class Application:
    """
    Main application class
    """

    def __init__(self):
        self.blender_file: str = ""

        self.config: dict[str, dict] | None = None

    def _parse(self):
        """
        Parse CLI arguments
        """

        parser = argparse.ArgumentParser(prog="Blender Camera Switcher")

        parser.add_argument("-i", "--input",
                            help="blender input file",
                            required=True)

        args = parser.parse_args()

        self.blender_file = args.input

    def _read_config(self):
        """
        Reads the config file
        """

        # read file
        with open("camera_ranges.json", "r") as file:
            self.config = json.load(file)

    def run(self):
        """
        Runs the application
        """

        # parse cli arguments
        self._parse()

        # read configs
        self._read_config()

        # open blender scene
        bpy.ops.wm.open_mainfile(filepath=self.blender_file)

    def render_camera(self, camera_name: str, range_start: int, range_end: int):
        """
        Renders frames from the perspective of the given camera in scene
        :param camera_name: name of the camera in scene
        :param range_start: frame starting range
        :param range_end: frame ending range
        """


def main():
    app = Application()
    app.run()


if __name__ == '__main__':
    main()
