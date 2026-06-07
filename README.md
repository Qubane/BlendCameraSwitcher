# BlendCameraSwitcher
Assign ranges of frames that need to be rendered

# How to use
- Used python 3.11+
- Was tested with blender 5.1.2
- To run the render use `python3.13 main.py [args]`

## Command line arguments
- `-i / --input` - .blend project
- `-s / --script` - camera sequencing script
- `--quality` - quality preset that will be used (defined in sequencing script)
- `--overwrite` - enable frame overwriting
- `-a / --accept` - skip the render question

## Sequencing script
- Basic example sequencing script is provided in `scripts/example.json`
- The format follows a simple structure:
  - `"render_options"`: dict
    - `"name_of_the_render_option"`: dict
      - `"resolution"`: `[1280, 720]` - list of width, height
      - `"noise_threshold"`: `0.05` - noise threshold for adaptive noise sampling
      - `"max_samples"`: `1024` - maximum number of samples
      - `"default_viewlayers"`: `["ViewLayer", "ViewLayer.001", ...]` - list of strings, with names of enabled by default viewlayers
  - `"render_ranges"`: dict
    - `"Camera.001"`: list
      - `"start"`: `1` - render range start
      - `"end"`: `250` - render range end
      - `"render_width"`: `1024` - overwrite rendering width
      - `"render_height"`: `1024` - overwrite rendering height
      - `"render_max_samples"`: `64` - overwrite max samples
      - `"render_noise_threshold"`: `0.1` - overwrite noise threshold
      - `"file_overwrite"`: `true / false` - enable / disable file overwrite
      - `"viewlayers"`: `["-", "ViewLayer.001"]` - additional viewlayers, the `"-"` disables all default viewlayers defined by the render option
      - `"python"`: `"bpy.data.objects['Cube'].hide_render = True"` - additional python script per camera angle