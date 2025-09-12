"""
Main file
"""


import os
import bpy
import json
import asyncio
import argparse
from tqdm import tqdm


class Application:
    """
    Main application class
    """

    def __init__(self):
        # argparser
        self.blender_file: str = ""
        self.output_directory: str = ""
        self.render_devices: list[str] = []
        self.batch_size: int = 10

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
        parser.add_argument("--render-devices",
                            help="blender used rendering devices separated by comma",
                            default="CPU")

        args = parser.parse_args()

        self.blender_file = args.input
        self.output_directory = args.output
        if not os.path.isdir(self.output_directory):
            os.makedirs(self.output_directory)
        self.render_devices = [x.strip() for x in args.render_devices.split(",") if x]

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
            else:
                break
        return range_start, render_range[1]

    async def _running_coro(self):
        """
        Running render coroutine
        """

        # render queue
        render_queue: list[dict[str, str | int]] = []

        # create queue
        device_switcher = 0
        for config_camera, config_data in self.config.items():
            for frame_range in config_data["ranges"]:
                # make directory path
                path = os.path.join(
                    os.getcwd(), self.output_directory, config_camera, f"{frame_range[0]}-{frame_range[1]}")

                # make sure directory exists
                if not os.path.isdir(path):
                    os.makedirs(path)

                # calculate new frame range
                new_frame_range = self.give_render_range(frame_range, path)

                # check if frame range is zero in length, and skip
                if new_frame_range[0] == new_frame_range[1]:
                    print(f"Skipped range {frame_range[0]} - {frame_range[1]} [{config_camera}]")
                    continue

                # split render range into batches
                for batch_idx in range(new_frame_range[0], new_frame_range[1], self.batch_size + 1):
                    # calculate rendering ranges
                    frame_range_start = batch_idx
                    frame_range_end = min(new_frame_range[1], batch_idx + self.batch_size)

                    # append command to queue
                    render_queue.append({
                        "frame_start": frame_range_start,
                        "frame_end": frame_range_end,
                        "path": path,
                        "camera": config_camera,
                        "device": self.render_devices[device_switcher]})

                    # change device
                    device_switcher = (device_switcher + 1) % len(self.render_devices)

        # assign rendering tasks
        tasks = []
        while len(render_queue) > 0:
            # fetch queue task
            queue_task = render_queue.pop(0)

            # append task
            tasks.append(asyncio.create_task(self.make_render_process(**queue_task)))

            # if there are equal (or more) amount of tasks and rendering devices start them
            if len(tasks) >= len(self.render_devices):
                await asyncio.gather(*tasks)

                # clear tasks
                tasks.clear()

    async def make_render_process(self, frame_start: int, frame_end: int, path: str, camera: str, device: str):
        """
        Makes a rendering process
        :param frame_start: frame starting range
        :param frame_end: frame ending range
        :param path: frame writing directory
        :param camera: assigned camera
        :param device: assigned device
        """

        # progress bar coroutine
        async def progress_bar_coro():
            # create progress bar
            progress_bar = tqdm(total=frame_end - frame_start, desc=f"Frames rendered [{device}]")

            # begin checking loop
            previous_frame = frame_start
            while previous_frame != frame_end:
                await asyncio.sleep(0.25)

                # check render range
                current_frame, _ = self.give_render_range((previous_frame, frame_end), path)

                # update progress bar
                progress_bar.update(current_frame - previous_frame)

                # set previous frame
                previous_frame = current_frame

            # after finishing close progress bar
            progress_bar.close()

        # make render command
        command = (f"blender "
                   f"-b "
                   f"\"{self.blender_file}\" "
                   f"-s {frame_start} "
                   f"-e {frame_end} "
                   f"-o \"{path}\\f_{'#' * self._blender_frame_digit_count}\" "
                   f"-P camera_switcher.py "
                   f"-a "
                   f"-- --camera-name \"{camera}\" "
                   f"--cycles-device {device}")

        # print
        print(f"Executing:\n\t{command}", end="\n\n")

        # start the progress bar
        task = asyncio.create_task(progress_bar_coro())

        # create subprocess
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()


def main():
    app = Application()
    app.run()


if __name__ == '__main__':
    main()
