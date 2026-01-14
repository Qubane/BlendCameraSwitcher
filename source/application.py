"""
Main application file
"""


import bpy
import json
import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class RenderOption:
    """
    Render option
    """

    resolution: tuple[int, int]
    noise_threshold: float
    max_samples: int


@dataclass(frozen=True)
class RenderRange:
    """
    Camera range
    """

    range_start: int
    range_end: int


class Application:
    """
    Main application class
    """

    def __init__(self):
        self.blender_file_path: str = ""

        self.render_quality: str = "preview"
        self.render_options: dict[RenderOption] | None = None
        self.render_ranges: dict[list[RenderRange]] | None = None

        self.render_frames_total: int = 0

        self.blender_framerate: int = 30
        self.blender_out_directory: str = "//tmp/"

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
        parser.add_argument(
            "--quality",
            help="pick render quality setting",
            default=self.render_quality)

        args = parser.parse_args()

        # save parsed arguments
        self.blender_file_path = args.input
        self.render_quality = args.quality

        self.render_options, self.render_ranges = self._parse_script_file(args.script)

    @staticmethod
    def _parse_script_file(path: str) -> tuple[dict, dict]:
        """
        Parses script file
        :param path: path to script file
        :return: dict
        """

        # read script
        with open(path, "r", encoding="utf-8") as file:
            script = json.load(file)

        render_options = {}
        render_ranges = {}

        # parse script
        # go through options
        for render_option_name, render_option in script["render_options"].items():
            # parse options
            render_options[render_option_name] = RenderOption(*render_option)
        # go through ranges
        for render_range_camera, render_ranges_list in script["render_ranges"].items():
            # create list of ranges for camera
            render_ranges[render_range_camera] = []
            # append ranges to that list
            for render_range in render_ranges_list:
                render_ranges[render_range_camera].append(RenderRange(*render_range))

        # return
        return render_options, render_ranges

    def run(self):
        """
        Runs the application
        """

        self.parse_args()

    def parse_blender_file(self, path: str):
        """
        Parses blender file
        :param path: path to blender file
        """

        # open blender file
        bpy.ops.wm.open_mainfile(filepath=path)

        # fetch framerate
        self.blender_framerate = bpy.context.scene.render.fps

        # check camera presence
        for camera in self.render_ranges.keys():
            if not bpy.data.objects.get(camera):
                raise KeyError(f"Missing camera with name '{camera}'")
