"""
Main application file
"""


import argparse


class Application:
    """
    Main application class
    """

    def __init__(self):
        self.blender_file_path: str = ""
        self.script_path: str = ""

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
        self.script_path = args.script

    def run(self):
        """
        Runs the application
        """

        self.parse_args()
