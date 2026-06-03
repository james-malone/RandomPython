"""
Turn a Google Street View image into ASCII art, ready to paste into a Reddit
post as a text-based GeoGuessr puzzle.

This script renders an image as luminance-mapped ASCII characters sized for a
monospace code block. The image can come from either source:

* --location: fetch a single panorama-facing image from the Google Street View
  Static API for an address or a "lat,lng" pair. Requires a Google Maps API key
  with the "Street View Static API" enabled, supplied with --api-key or via the
  GOOGLE_STREET_VIEW_API_KEY (or GOOGLE_API_KEY) environment variable. These
  requests are billed by Google, so use them responsibly.
* --image: read a local image file instead (e.g. a screenshot you grabbed from
  Street View yourself). No API key, no network, no billing.

Examples:

    python streetview_ascii.py --location "48.8584,2.2945" --heading 230 \
        --width 80 --reddit --out puzzle.txt

    python streetview_ascii.py --image street_view_screenshot.png \
        --width 80 --reddit --out puzzle.txt

@author - James Malone
"""

# Imports for this script
import argparse
import os
import sys

import requests
from PIL import Image, ImageOps

# Constant variables
STATIC_URL = 'https://maps.googleapis.com/maps/api/streetview'
METADATA_URL = 'https://maps.googleapis.com/maps/api/streetview/metadata'
API_KEY_ENV_VARS = ['GOOGLE_STREET_VIEW_API_KEY', 'GOOGLE_API_KEY']

# Character ramp from darkest (dense) to lightest (sparse). Dark image pixels
# map to the leftmost glyphs, so the default looks correct on a light/white
# background. Use --invert for a dark background (e.g. Reddit dark mode).
DEFAULT_CHARS = '@%#*+=-:. '

# Monospace cells are roughly twice as tall as they are wide, so the row count
# is scaled by this factor to keep the picture from looking vertically stretched.
DEFAULT_CHAR_ASPECT = 0.5

# Street View Static caps standard (unsigned) requests at 640x640.
DEFAULT_IMAGE_SIZE = '640x640'

# Reddit renders an indented block as monospaced code on both old and new Reddit.
REDDIT_INDENT = '    '

# HTTP request timeout, in seconds.
REQUEST_TIMEOUT = 30


def resolve_api_key(cli_key):
    """
    Return the API key from the command line if given, otherwise fall back to
    the supported environment variables. Returns None if no key is found.
    """
    if cli_key:
        return cli_key
    for env_var in API_KEY_ENV_VARS:
        if os.environ.get(env_var):
            return os.environ[env_var]
    return None


def check_imagery_available(location, heading, pitch, fov, api_key):
    """
    Hit the (free, non-billed) Street View metadata endpoint to confirm imagery
    exists at the requested location before fetching the actual image. Returns a
    tuple of (status, friendly_location_string). Raises on transport errors.
    """
    params = {
        'location': location,
        'heading': heading,
        'pitch': pitch,
        'fov': fov,
        'key': api_key,
    }
    response = requests.get(METADATA_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    return data.get('status'), data.get('location')


def fetch_streetview_image(location, heading, pitch, fov, size, api_key):
    """
    Fetch a Street View Static image for the given parameters and return it as a
    PIL Image. Raises a ValueError if Google returns a non-image response.
    """
    params = {
        'size': size,
        'location': location,
        'heading': heading,
        'pitch': pitch,
        'fov': fov,
        'key': api_key,
    }
    response = requests.get(STATIC_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    content_type = response.headers.get('Content-Type', '')
    if 'image' not in content_type:
        raise ValueError(
            'Expected an image from Street View but got "%s": %s'
            % (content_type, response.text[:200])
        )

    from io import BytesIO
    return Image.open(BytesIO(response.content))


def image_to_ascii(image, width, chars, char_aspect, invert, autocontrast):
    """
    Convert a PIL Image into an ASCII-art string. The image is resized to the
    requested character width (rows scaled by char_aspect to compensate for tall
    monospace cells), converted to grayscale, and each pixel is mapped onto the
    character ramp by brightness.
    """
    # Grayscale, with an optional contrast stretch that makes the art pop.
    gray = image.convert('L')
    if autocontrast:
        gray = ImageOps.autocontrast(gray)

    # Work out the target row count from the source aspect ratio.
    source_width, source_height = gray.size
    aspect = source_height / source_width
    height = max(1, int(width * aspect * char_aspect))
    gray = gray.resize((width, height))

    # By default, dark pixels map to the dense leading glyph and bright pixels
    # to the trailing space, which reads correctly on a light background. For a
    # dark background (e.g. Reddit dark mode) reverse the ramp so the bright
    # subject is drawn with the dense glyphs instead.
    ramp = chars[::-1] if invert else chars
    scale = (len(ramp) - 1) / 255.0

    # For an 'L' image this is one byte per pixel, i.e. the grayscale values.
    pixels = gray.tobytes()
    rows = []
    for row_index in range(height):
        start = row_index * width
        row_pixels = pixels[start:start + width]
        rows.append(''.join(ramp[int(value * scale)] for value in row_pixels))
    return '\n'.join(rows)


def format_for_reddit(ascii_art):
    """
    Indent every line by four spaces so Reddit renders the art as a monospace
    code block (works on both old and new Reddit).
    """
    return '\n'.join(REDDIT_INDENT + line for line in ascii_art.split('\n'))


def build_arg_parser():
    """
    Build and return the argument parser for this script.
    """
    parser = argparse.ArgumentParser(
        description='Turn a Google Street View image into Reddit-ready ASCII art.'
    )
    parser.add_argument('-l', '--location',
                        help='Address or "lat,lng" pair to look at.')
    parser.add_argument('-i', '--image',
                        help='Use a local image file instead of fetching from '
                             'Street View (e.g. a screenshot). No API key needed.')
    parser.add_argument('--heading', type=float, default=0,
                        help='Compass heading of the camera, 0-360 (default 0).')
    parser.add_argument('--pitch', type=float, default=0,
                        help='Up/down angle, -90 to 90 (default 0).')
    parser.add_argument('--fov', type=float, default=90,
                        help='Field of view / zoom, max 120 (default 90).')
    parser.add_argument('-w', '--width', type=int, default=80,
                        help='Output width in characters (default 80).')
    parser.add_argument('--chars', default=DEFAULT_CHARS,
                        help='Character ramp from darkest to lightest.')
    parser.add_argument('--char-aspect', type=float, default=DEFAULT_CHAR_ASPECT,
                        help='Row scaling for tall monospace cells (default 0.5).')
    parser.add_argument('--invert', action='store_true',
                        help='Invert brightness mapping for dark backgrounds.')
    parser.add_argument('--no-autocontrast', action='store_true',
                        help='Disable the automatic contrast stretch.')
    parser.add_argument('--size', default=DEFAULT_IMAGE_SIZE,
                        help='Source image size, e.g. 640x640 (default 640x640).')
    parser.add_argument('--reddit', action='store_true',
                        help='Indent output as a Reddit code block.')
    parser.add_argument('-o', '--out',
                        help='Also write the ASCII output to this file.')
    parser.add_argument('--api-key',
                        help='Google Maps API key (else uses env vars).')
    return parser


def main():
    """
    Main method - executes work for this script.
    """
    parser = build_arg_parser()
    args = parser.parse_args()

    # Exactly one image source: a local file, or a Street View lookup.
    if bool(args.image) == bool(args.location):
        parser.error('provide exactly one of --image or --location.')

    if args.image:
        # Local file path: no API key, no network, no billing.
        try:
            image = Image.open(args.image)
        except (FileNotFoundError, OSError) as error:
            sys.exit('Could not open image "%s": %s' % (args.image, error))
    else:
        api_key = resolve_api_key(args.api_key)
        if not api_key:
            sys.exit(
                'No API key found. Pass --api-key, set one of: %s, '
                'or use --image with a local file instead.'
                % ', '.join(API_KEY_ENV_VARS)
            )

        # Confirm there is actually imagery here before spending a billed request.
        status, resolved = check_imagery_available(
            args.location, args.heading, args.pitch, args.fov, api_key)
        if status != 'OK':
            sys.exit(
                'No Street View imagery for "%s" (metadata status: %s).'
                % (args.location, status)
            )
        if resolved:
            print('Found imagery near %s' % resolved, file=sys.stderr)

        image = fetch_streetview_image(
            args.location, args.heading, args.pitch, args.fov, args.size, api_key)

    ascii_art = image_to_ascii(
        image,
        width=args.width,
        chars=args.chars,
        char_aspect=args.char_aspect,
        invert=args.invert,
        autocontrast=not args.no_autocontrast,
    )

    output = format_for_reddit(ascii_art) if args.reddit else ascii_art

    if args.out:
        with open(args.out, 'w') as out_file:
            out_file.write(output + '\n')
        print('Wrote ASCII art to %s' % args.out, file=sys.stderr)

    print(output)


if __name__ == '__main__':
    main()
