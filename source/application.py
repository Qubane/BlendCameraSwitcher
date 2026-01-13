"""
Main application file
"""


import json
import argparse


class Application:
    """
    Main application class
    """

    def __init__(self):
        self.blender_file_path: str = ""
        self.script: dict[str, list[list]] | None = None

    def parse_args(self):
        """
        Parses CLI arguments
        """

        # define parser
        parser = argparse.ArgumentParser(prog="Blender Camera Switcher", description="Automatically switch cameras")

        parser.add_argument(
            "-i", "--input",
            help="blender input file",
            required=True)
        parser.add_argument(
            "-s", "--script",
            help="camera sequence script",
            required=True)

        args = parser.parse_args()

        # save parsed arguments
        self.blender_file_path = args.input
        self.script = self._read_script_file(args.script)

    @staticmethod
    def _read_script_file(path: str) -> dict[str, list[list]]:
        """
        Parses script file
        :param path: path to script file
        :return: dict
        """

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def run(self):
        """
        Runs the application
        """

        self.parse_args()
