"""
Main file
"""


import os
import bpy
import json
import argparse


class Application:
    """
    Main application class
    """

    def __init__(self):
        self.blender_file: str = ""
        self.output_directory: str = ""

        self.scene_cameras: list = []

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

        # read cameras
        self.scene_cameras = [obj for obj in bpy.data.objects if obj.type == 'CAMERA']
        scene_camera_names = [camera.name for camera in self.scene_cameras]

        # ensure the cameras are present in config
        for config_camera in self.config.keys():
            if config_camera not in scene_camera_names:
                raise KeyError(f"Camera '{config_camera}' not found!")

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

            # make sure the directory for output is present
            if not os.path.isdir(path):
                os.makedirs(path)

            # assign path to blender output
            bpy.context.scene.render.filepath = os.path.join(path, "f_")

            # go through ranges and render them
            for frame_range in config_data["ranges"]:
                self.render_camera(config_camera, frame_range[0], frame_range[1])

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
        bpy.ops.render.render(animation=True)


def main():
    app = Application()
    app.run()


if __name__ == '__main__':
    main()
