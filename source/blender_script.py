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
    parser.add_argument("--render-width", type=int)
    parser.add_argument("--render-height", type=int)
    parser.add_argument("--render-noise-threshold", type=float)
    parser.add_argument("--render-max-samples", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--viewlayers", type=str)

    # parse arguments after the first `--`
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:])


def main():
    args = parse_args()

    # fetch and update target camera
    bpy.context.scene.camera = bpy.data.objects.get(args.camera[1:-1])

    # update render width and height
    bpy.context.scene.render.resolution_x = args.render_width
    bpy.context.scene.render.resolution_y = args.render_height
    bpy.context.scene.render.resolution_percentage = 100  # make sure the percentage is 100%

    # update noise threshold
    bpy.context.scene.cycles.use_adaptive_sampling = True  # make sure adaptive sampling is enabled
    bpy.context.scene.cycles.adaptive_threshold = args.render_noise_threshold

    # update max samples
    bpy.context.scene.cycles.samples = args.render_max_samples

    # disable all viewlayers
    for view_layer in bpy.context.scene.view_layers:
        view_layer.use = False

    # fetch and activate set viewlayers
    if args.viewlayers is not None:
        for view_layer in args.viewlayers.split(","):
            view_layer_obj = bpy.context.scene.view_layers.get(view_layer)
            if view_layer_obj is not None:
                view_layer_obj.use = True

    # # jank fix
    # if len(args.viewlayers.split(",")) > 1:
    #     bpy.context.scene.render.use_persistent_data = False
    # else:
    #     bpy.context.scene.render.use_persistent_data = True

    # update view layer
    bpy.context.evaluated_depsgraph_get().update()

    # update overwrite flag
    bpy.context.scene.render.use_overwrite = args.overwrite


if __name__ == "__main__":
    main()
