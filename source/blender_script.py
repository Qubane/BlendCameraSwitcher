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
    parser.add_argument("--camera")
    parser.add_argument("--overwrite", action="store_true")

    # parse arguments after the first `--`
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:])
