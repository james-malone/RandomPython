RandomPython
============

Random bits and pieces of python to make life more interesting.

# List of scripts
* `airnow_history_grabber.py` - Grabs historical AirNow air quality data
* `grab_walkscore_data.py` - Grabs score data from the Walkscore page for a given CSV list of cities (walk, bike, and transit scores)
* `streetview_ascii.py` - Turns a Google Street View image into ASCII art, ready to paste into a Reddit post as a text-based GeoGuessr puzzle

## streetview_ascii.py

Fetches a Street View Static image for a location and renders it as
luminance-mapped ASCII art sized for a monospace code block.

Requires a Google Maps API key with the **Street View Static API** enabled,
supplied via `--api-key` or the `GOOGLE_STREET_VIEW_API_KEY` (or
`GOOGLE_API_KEY`) environment variable. Needs `requests` and `Pillow`.

```
export GOOGLE_STREET_VIEW_API_KEY="your-key"
python streetview_ascii.py --location "48.8584,2.2945" --heading 230 \
    --width 80 --reddit --out puzzle.txt
```

Notes:
* `--location` accepts an address or a `lat,lng` pair.
* `--heading`, `--pitch`, and `--fov` aim/zoom the camera.
* `--reddit` indents every line by four spaces so it renders as a code block on
  old and new Reddit; paste the output straight into your post.
* Default brightness mapping suits a light background. Use `--invert` for
  Reddit dark mode.
* A free metadata check runs first so you don't spend a billed image request on
  a spot with no Street View coverage.
