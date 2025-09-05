"""
Main file
"""


import os
import sys
import bpy
import json
import argparse
from contextlib import contextmanager


@contextmanager
def stdout_redirected(to=os.devnull):
    """
    import os

    with stdout_redirected(to=filename):
        print("from Python")
        os.system("echo non-Python applications are also supported")
    """

    fd = sys.stdout.fileno()

    def _redirect_stdout(redirect):
        sys.stdout.close()
        os.dup2(redirect.fileno(), fd)
        sys.stdout = os.fdopen(fd, 'w')

    with os.fdopen(os.dup(fd), 'w') as old_stdout:
        with open(to, 'w') as file:
            _redirect_stdout(redirect=file)
        try:
            yield
        finally:
            _redirect_stdout(redirect=old_stdout)


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

        # make render
        for config_camera, config_data in self.config.items():
            path = config_data.get("path")

            # if path was not provided
            if path is None:
                path = os.path.join(self.output_directory, config_camera)

            # if path is relative
            elif path[:2].replace("\\", "/") == "//":
                path = os.path.join(self.output_directory, path[2:])

            # make sure the path is absolute
            path = os.path.join(os.getcwd(), path)

            # go through ranges and render them
            for frame_range in config_data["ranges"]:
                # make range path
                range_path = os.path.join(path, f"{frame_range[0]}-{frame_range[1]}")

                # make sure the directory for output is present
                if not os.path.isdir(range_path):
                    os.makedirs(range_path)

                # assign path to blender output
                bpy.context.scene.render.filepath = os.path.join(range_path, "f_")

                # print current range
                print(f"Rendering camera '{config_camera}' range {frame_range[0]}..{frame_range[1]}")

                # render
                self.render_camera(config_camera, frame_range[0], frame_range[1])

                # print finish
                print(f"Done rendering {frame_range[1] - frame_range[0]} frames;", end="\n\n")

    def render_camera(self, camera_name: str, range_start: int, range_end: int):
        """
        Renders frames from the perspective of the given camera in scene
        :param camera_name: name of the camera in scene
        :param range_start: frame starting range
        :param range_end: frame ending range
        """

        # update frame ranges
        bpy.context.scene.frame_start = range_start
        bpy.context.scene.frame_end = range_end

        # switch camera
        camera = [camera for camera in self.scene_cameras if camera.name == camera_name][0]
        bpy.context.scene.camera = camera

        # update view
        bpy.context.view_layer.update()

        # do render
        with stdout_redirected():
            bpy.ops.render.render(animation=True)


def main():
    app = Application()
    app.run()


if __name__ == '__main__':
    main()
