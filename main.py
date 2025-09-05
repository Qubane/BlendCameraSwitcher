"""
Main file
"""


import os
import sys
import bpy
import json
import asyncio
import argparse
from contextlib import contextmanager


class Application:
    """
    Main application class
    """

    def __init__(self):
        # argparser
        self.blender_file: str = ""
        self.output_directory: str = ""
        self.render_device: str = ""

        # config
        self.config: dict[str, dict] | None = None

        # magic number
        self._blender_frame_digit_count: int = 6

    def _parse(self):
        """
        Parse CLI arguments
        """

        parser = argparse.ArgumentParser(prog="Blender Camera Switcher")

        parser.add_argument("-i", "--input",
                            help="blender input file",
                            required=True)
        parser.add_argument("-o", "--output",
                            help="blender output directory",
                            default="frames")
        parser.add_argument("--render-device",
                            help="blender used rendering device",
                            default="CPU",
                            choices=["CPU", "CUDA", "OPTIX", "HIP", "ONEAPI"])

        args = parser.parse_args()

        self.blender_file = args.input
        self.output_directory = args.output
        if not os.path.isdir(self.output_directory):
            os.makedirs(self.output_directory)
        self.render_device = args.render_device

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

        # ensure the cameras are present in config
        for config_camera in self.config.keys():
            if bpy.data.objects.get(config_camera) is None:
                raise KeyError(f"Camera '{config_camera}' not found!")

        # count number of frames
        scene_framerate = bpy.context.scene.render.fps
        total_frame_count = 0
        for _, config_data in self.config.items():
            for frame_range in config_data["ranges"]:
                delta = frame_range[1] - frame_range[0]
                if delta < 0:
                    raise ValueError("Negative frame delta range")
                total_frame_count += delta + 1

        # print frame metadata
        print(f"Total frame count is {total_frame_count} frames, at {scene_framerate} fps;")
        print(f"Scene duration is {total_frame_count / scene_framerate / 60:.2f} minutes;")

        # print rendering metadata
        print(f"Scene rendering engine set to '{bpy.context.scene.render.engine}';")

        resolution_x = int(bpy.context.scene.render.resolution_x * bpy.context.scene.render.resolution_percentage / 100)
        resolution_y = int(bpy.context.scene.render.resolution_y * bpy.context.scene.render.resolution_percentage / 100)
        print(f"Scene resolution set to {resolution_x}x{resolution_y}")

        # separator
        print()

        # start coro
        asyncio.run(self._running_coro())

    def give_render_range(self, render_range: tuple[int, int], path: str) -> tuple[int, int]:
        """
        Counts frames and gives the appropriate number of frames that still need to be rendered.
        Used to avoid starting blender process and closing it after rendering 0 frames.
        :param render_range: rendering range (range that will be checked)
        :param path: path to frames
        :return: new range
        """

        range_start = render_range[0]
        for frame_idx in range(render_range[0], render_range[1] + 1):
            frame_format = bpy.context.scene.render.image_settings.file_format.lower()
            frame_path = os.path.join(path, f"f_{frame_idx:0>{self._blender_frame_digit_count}}.{frame_format}")
            if os.path.isfile(frame_path):
                range_start = frame_idx
        return range_start, render_range[1]

    async def _running_coro(self):
        """
        Running render coroutine
        """

        for config_camera, config_data in self.config.items():
            for frame_range in config_data["ranges"]:
                # make directory path
                path = os.path.join(
                    os.getcwd(), self.output_directory, config_camera, f"{frame_range[0]}-{frame_range[1]}")

                # make sure directory exists
                if not os.path.isdir(path):
                    os.makedirs(path)

                # calculate frame range
                frame_range = self.give_render_range(frame_range, path)

                # check if frame range is zero in length, and skip
                if frame_range[0] == frame_range[1]:
                    print(f"Skipped range {frame_range[0]} - {frame_range[1]}")
                    continue

                # make render command
                command = (f"blender "
                           f"-b "
                           f"\"{self.blender_file}\" "
                           f"-s {frame_range[0]} "
                           f"-e {frame_range[1]} "
                           f"-o \"{path}\\f_{'#' * self._blender_frame_digit_count}\" "
                           f"-P camera_switcher.py "
                           f"-a "
                           f"-- --camera-name \"{config_camera}\" "
                           f"--cycles-device {self.render_device}")

                # start rendering process
                await self.make_render_process(command)

    @staticmethod
    async def make_render_process(command: str):
        """
        Makes a rendering process
        :param command: shell command
        """

        # print
        print(f"Executing:\n\t{command}")

        # create subprocess
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()

        # print
        print(stdout.decode("ASCII"), end="\n\n")


def main():
    app = Application()
    app.run()


if __name__ == '__main__':
    main()
