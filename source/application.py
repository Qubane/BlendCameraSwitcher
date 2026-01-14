"""
Main application file
"""


import os
import bpy
import json
import argparse
import subprocess
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
    actual_range_start: int = 0


class Application:
    """
    Main application class
    """

    def __init__(self):
        self.blender_file_path: str = ""

        self.render_overwrite: bool = False
        self.render_quality: str = "preview"
        self.render_options: dict[str, RenderOption] | None = None
        self.render_ranges: dict[str, list[RenderRange]] | None = None

        self.render_frames_total: int = 0

        self.blender_framerate: int = 30
        self.blender_out_directory: str = "//tmp/"

        self._frame_filepath: str = "{camera}/{range}/"
        self._frame_filename: str = "######.{ext}"

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
        parser.add_argument(
            "--overwrite",
            help="overwrite the rendered frames",
            action='store_true')

        args = parser.parse_args()

        # save parsed arguments
        self.blender_file_path = args.input
        self.render_quality = args.quality
        self.render_overwrite = args.overwrite

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
            render_options[render_option_name] = RenderOption(*render_option.values())
        # go through ranges
        for render_range_camera, render_ranges_list in script["render_ranges"].items():
            # create list of ranges for camera
            render_ranges[render_range_camera] = []
            # append ranges to that list
            for render_range in render_ranges_list:
                render_ranges[render_range_camera].append(RenderRange(*render_range))

        # return
        return render_options, render_ranges

    @staticmethod
    def _render_range_path(render_range: RenderRange) -> str:
        """
        Returns render range path
        :param render_range: render range
        :return: path
        """

        return f"{render_range.range_start}-{render_range.range_end}"

    def run(self):
        """
        Runs the application
        """

        self.parse_args()
        self.parse_blender_file(self.blender_file_path)
        self._make_directories()
        self._update_ranges()
        self.begin_render()

    def _make_directories(self):
        """
        Makes output directories
        """

        # make main output directory
        os.makedirs(self.blender_out_directory, exist_ok=True)

        # make directories for cameras and camera render ranges
        for camera, camera_render_ranges in self.render_ranges.items():
            for render_range in camera_render_ranges:
                path = os.path.join(self.blender_out_directory, camera, self._render_range_path(render_range))
                os.makedirs(path, exist_ok=True)

    def _update_ranges(self):
        """
        Updates ranges for rendering
        """

        # generate f-string file format
        file_format = (self._frame_filename
                       .replace("#", f"{{num:0>{self._frame_filename.count('#')}}}", 1)
                       .replace("#", ""))

        # go through cameras
        for camera, camera_ranges in self.render_ranges.items():
            # go through camera render ranges
            for idx, render_range in enumerate(camera_ranges):
                # generate directory path to camera and camera range
                check_path = os.path.join(self.blender_out_directory, camera, self._render_range_path(render_range))

                # go through frames and skip frames if they are already present
                actual_range_start = render_range.range_start
                if not self.render_overwrite:
                    for frame in range(render_range.range_start, render_range.range_end + 1):
                        # create filepath to check
                        filepath = os.path.join(check_path, file_format.format(num=frame))

                        # if frame with in that range is already present -> increment the actual range start to skip it
                        # during rendering phase
                        if os.path.isfile(filepath):
                            actual_range_start += 1
                        else:
                            break

                # update the camera range
                camera_ranges[idx] = RenderRange(render_range.range_start, render_range.range_end, actual_range_start)

            # go through camera render ranges and delete ones with delta <= 0
            idx = 0
            while idx < len(camera_ranges):
                if camera_ranges[idx].range_end - camera_ranges[idx].actual_range_start <= 0:
                    camera_ranges.pop(idx)
                    idx -= 1
                idx += 1

    def parse_blender_file(self, path: str):
        """
        Parses blender file
        :param path: path to blender file
        """

        # open blender file
        bpy.ops.wm.open_mainfile(filepath=path)

        # fetch basic info
        self.blender_framerate: int = bpy.context.scene.render.fps
        self.blender_out_directory: str = bpy.context.scene.render.filepath
        self._frame_filename = self._frame_filename.format(
            ext=bpy.context.scene.render.image_settings.file_format.lower())

        # make path
        self.blender_out_directory = (self.blender_out_directory
                                      .replace("\\", "/")
                                      .replace("//", os.path.dirname(path) + "/"))

        # check camera presence
        for camera in self.render_ranges.keys():
            if not bpy.data.objects.get(camera):
                raise KeyError(f"Missing camera with name '{camera}'")

    def begin_render(self):
        """
        Starts the actual rendering
        """

        # get option preset
        render_option = self.render_options[self.render_quality]

        # go through cameras
        for camera, camera_ranges in self.render_ranges.items():
            # go through camera render ranges
            for render_range in camera_ranges:
                # create output path
                output_path = os.path.join(
                    self.blender_out_directory,
                    camera,
                    self._render_range_path(render_range),
                    self._frame_filename)

                # generate CLI command
                command = (f"blender "
                           f"-b \"{self.blender_file_path}\" "
                           f"-s {render_range.actual_range_start} "
                           f"-e {render_range.range_end} "
                           f"-o \"{output_path}\" "
                           f"-P \"source/blender_script.py\" "
                           f"-a "
                           f"-- "
                           f"--camera '{camera}' "
                           f"--render-width {render_option.resolution[0]} "
                           f"--render-height {render_option.resolution[1]} "
                           f"--render-noise-threshold {render_option.noise_threshold} "
                           f"--render-max-samples {render_option.max_samples}"
                           f"{'--overwrite' if self.render_overwrite else ''}")

                # execute the command
                subprocess.run(command)
