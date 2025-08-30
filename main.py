"""
Main file
"""


import argparse


class Application:
    """
    Main application class
    """

    def __init__(self):
        self.blender_file: str = ""

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

    def run(self):
        """
        Runs the application
        """


def main():
    app = Application()
    app.run()


if __name__ == '__main__':
    main()
