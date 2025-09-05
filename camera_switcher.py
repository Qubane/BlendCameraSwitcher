"""
Used for switching camera in blender file
"""


import bpy
import sys
import argparse


def parse_args():
    """
    Parses CLI arguments
    """

    parser = argparse.ArgumentParser(description='Set the active camera in a Blender scene.')
    parser.add_argument('--camera-name')
    parser.add_argument('--cycles-device',
                        choices=['CPU', 'CUDA', "OPTIX", "HIP"],
                        default='CPU')

    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


if __name__ == "__main__":
    args = parse_args()

    # Set the name of the camera you want to set active from command-line argument
    target_camera_name = args.camera_name

    # Find the camera object by its name
    camera_obj = bpy.data.objects.get(target_camera_name)

    # if camera was not found
    if camera_obj is None:
        raise KeyError("Camera not found")
    else:
        # Set this camera as the active camera
        bpy.context.scene.camera = camera_obj

        # update view
        bpy.context.view_layer.update()

    # switch rendering device
    cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
    cycles_prefs.get_devices()
    if args.cycles_device != "CPU":
        bpy.context.scene.cycles.device = "GPU"
        cycles_prefs.compute_device_type = args.cycles_device

        for device in cycles_prefs.devices:
            if args.cycles_device in device.type:
                device.use = True
    else:
        bpy.context.scene.cycles.device = "CPU"

    # disable overwrites
    bpy.context.scene.render.use_overwrite = False
