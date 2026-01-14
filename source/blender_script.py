"""
Script that will be passed to blender in CLI command
"""


import bpy
import sys
import argparse


def parse_args():
    """
    Parses CLI arguments
    """

    # define parse
    parser = argparse.ArgumentParser(description="Script that is passed to blender")

    # define arguments
    parser.add_argument("--camera", required=True)
    parser.add_argument("--overwrite", action="store_true")

    # parse arguments after the first `--`
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:])


def main():
    args = parse_args()

    # fetch and update target camera
    bpy.context.scene.camera = bpy.data.objects.get(args.camera)

    # update view layer
    bpy.context.view_layer.update()

    # update overwrite flag
    bpy.context.scene.render.use_overwrite = args.overwrite


if __name__ == "__main__":
    main()
