"""
Main application file
"""


import os
import bpy
import json
import copy
import base64
import argparse
import subprocess
from datetime import datetime


class Application:
    """
    Main application class
    """

    def __init__(self):
        self.project_path: str = ""
        self.project_quality: str = "preview"
        self.project_script: str = ""

        self.blender_out_directory: str = "//tmp/"
        self.blender_frame_name: str = "{num:0>6}"

        self.render_width: int = -1
        self.render_height: int = -1
        self.render_noise_threshold: float = -1
        self.render_file_overwrite: bool = False
        self.render_max_samples: int = -1
        self.render_default_viewlayers: list[str] = []
        self.render_framerate: int = 30

        self.render_script: dict[str, list[dict]] = {}

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
            default=self.project_quality)
        parser.add_argument(
            "--overwrite",
            help="overwrite the rendered frames",
            action='store_true')

        args = parser.parse_args()

        self.project_path = args.input
        self.project_script = args.script
        self.project_quality = args.quality

        self.render_file_overwrite = args.overwrite

    def parse_project_script(self):
        """
        Parses project rendering script
        """

        # open file
        with open(self.project_script, "r", encoding="utf-8") as file:
            render_script = json.load(file)

        # set rendering defaults
        render_option = render_script["render_options"][self.project_quality]
        self.render_width = render_option["resolution"][0]
        self.render_height = render_option["resolution"][1]
        self.render_max_samples = render_option["max_samples"]
        self.render_noise_threshold = render_option["noise_threshold"]
        self.render_default_viewlayers = render_option["default_viewlayers"]

        # set rendering script
        self.render_script = render_script["render_ranges"]

    def parse_blender_file(self):
        """
        Parses blender file
        """

        # open blender file
        bpy.ops.wm.open_mainfile(filepath=self.project_path)

        # fetch basic info
        self.render_framerate = bpy.context.scene.render.fps
        self.blender_out_directory = bpy.context.scene.render.filepath
        self.blender_frame_name += bpy.context.scene.render.file_extension.lower()

        # make path
        self.blender_out_directory = (self.blender_out_directory
                                      .replace("\\", "/")
                                      .replace("//", os.path.dirname(self.project_path) + "/"))

        # check camera presence
        for camera in self.render_script.keys():
            if not bpy.data.objects.get(camera):
                raise KeyError(f"Missing camera with name '{camera}'")

    def directory_path(self, camera: str, frame_range: dict) -> str:
        """
        Creates a path to directory using camera parameters
        :param camera: camera name
        :param frame_range: camera render script parameters
        :return: path to directory
        """

        frame_start = frame_range.get("initial_start", frame_range["start"])
        camera_range = f"{frame_start}-{frame_range['end']}"

        camera_viewlayers = ""
        if "viewlayers" in frame_range:
            camera_viewlayers = f" [{','.join(x for x in frame_range['viewlayers'])}]"

        return os.path.join(self.blender_out_directory, camera, camera_range + camera_viewlayers)

    def create_output_directories(self):
        """
        Creates frame output directories
        """

        # create output directories
        for camera, frame_ranges in self.render_script.items():
            for frame_range in frame_ranges:
                path = self.directory_path(camera, frame_range)
                os.makedirs(path, exist_ok=True)

    def update_render_ranges(self):
        """
        Updates internal render ranges when overwriting is disabled
        """

        for camera, frame_ranges in self.render_script.items():
            for frame_range in frame_ranges:
                path = self.directory_path(camera, frame_range)
                frame_range["initial_start"] = frame_range["start"]
                for i in range(frame_range["start"], frame_range["end"] + 1):
                    if os.path.isfile(os.path.join(path, self.blender_frame_name.format(num=i))):
                        frame_range["start"] = i
                    else:
                        break

    def print_information(self):
        """
        Prints out some information about what is going to be rendered
        """

        # count total number of frames
        total_render_frames = 0
        actual_total_render_frames = 0
        for camera, frame_ranges in self.render_script.items():
            for frame_range in frame_ranges:
                total_render_frames += frame_range["end"] - frame_range["start"]
                actual_total_render_frames += frame_range["end"] - frame_range["initial_start"]

        # total time
        total_runtime = total_render_frames / self.render_framerate
        total_runtime_actual = actual_total_render_frames / self.render_framerate

        print("Information:")
        print(f"\tFrames to render: {total_render_frames} [{actual_total_render_frames}]")
        print(f"\tTotal animation length: {total_runtime:.2f} [{total_runtime_actual:.2f}] sec")
        print(f"\tRender quality: {self.project_quality}")
        print(f"\tRender resolution: {self.render_width}x{self.render_height}")
        print(f"\tRender noise threshold: {self.render_noise_threshold}")
        print(f"\tRender max sample count: {self.render_max_samples}")

    def run(self):
        """
        Runs the application
        """

        self.parse_args()
        self.parse_project_script()
        self.parse_blender_file()
        self.create_output_directories()

        if not self.render_file_overwrite:
            self.update_render_ranges()

        self.print_information()

        try:
            self.begin_render()
        except KeyboardInterrupt:
            self.quick_log("RENDER INTERRUPT")

    def quick_log(self, new_line: str):
        """
        Quick render log
        :param new_line: line to add to it
        """

        path = os.path.join(os.path.dirname(self.project_path), "render.log")
        with open(path, "a", encoding="utf-8") as file:
            file.write(datetime.now().strftime("[%d/%m/%Y %H:%M:%S] ") + new_line + "\n")

    def begin_render(self):
        """
        Starts the actual rendering
        """

        self.quick_log("RENDER START")
        for camera, frame_ranges in self.render_script.items():
            for frame_range in frame_ranges:
                # process overrides
                render_settings = {
                    "start": frame_range["start"],
                    "end": frame_range["end"],
                    "render_width": self.render_width,
                    "render_height": self.render_height,
                    "render_max_samples": self.render_max_samples,
                    "render_noise_threshold": self.render_noise_threshold,
                    "file_overwrite": self.render_file_overwrite,
                    "viewlayers": self.render_default_viewlayers,
                    "python": ""}

                # set overrides
                for key, value in frame_range.items():
                    if key == "start" or key == "end":
                        continue
                    render_settings[key] = copy.copy(value)

                    # viewlayers
                    if key == "viewlayers":
                        flag_set = False
                        for viewlayer in render_settings[key][::]:
                            if viewlayer == "-":
                                render_settings[key].remove(viewlayer)
                                flag_set = True
                        if not flag_set:
                            render_settings[key] += self.render_default_viewlayers

                # if frame are overwritten
                if render_settings["file_overwrite"]:
                    render_settings["start"] = frame_range["initial_start"]

                # skip zero frame range
                if render_settings["end"] - render_settings["start"] <= 0:
                    continue

                # generate output path
                output_path = os.path.join(
                    self.directory_path(camera, frame_range),
                    self.blender_frame_name.format(num=0).replace("0", "#"))

                # generate viewlayers
                viewlayers = ",".join(render_settings["viewlayers"])

                # encode python script
                python_code = base64.b64encode(render_settings["python"].encode("UTF-8")).decode("ASCII")
                python_code = f"'{python_code}'"

                # generate CLI command
                command = (f"blender "
                           f"-b \"{self.project_path}\" "
                           f"-s {render_settings['start']} "
                           f"-e {render_settings['end']} "
                           f"-o \"{output_path}\" "
                           f"-P \"source/blender_script.py\" "
                           f"-a "
                           f"-- "
                           f"--camera '{camera}' "
                           f"--render-width {render_settings['render_width']} "
                           f"--render-height {render_settings['render_height']} "
                           f"--render-noise-threshold {render_settings['render_noise_threshold']} "
                           f"--render-max-samples {render_settings['render_max_samples']} "
                           f"{'--overwrite' if render_settings['file_overwrite'] else ''} "
                           f"{f'--viewlayers {viewlayers}' if viewlayers else ''} "
                           f"{f'--python {python_code}' if python_code else ''} ")

                self.quick_log(f"EXECUTING `{command}`")

                # execute the command
                subprocess.run(command)
        self.quick_log("RENDER END")
